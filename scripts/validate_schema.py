"""Contract-based schema validation for real-data ingestion.

Hard gate applied ONLY to files taken from data/raw/ under data_mode='real'.
Validates a real CSV against its data/contracts/{table}_schema.yml before the
file is allowed into bronze/silver. Not reachable from the demo path — the
single production call site is inside the `data_mode == "real"` branch of
scripts/ingest_raw.py, so data/sample/*.csv is never validated and loads
regardless of content.

SEVERITY (cycle 1b-i ruling)
---------------------------
Violations carry a severity, because "the file is the wrong shape" and "this
row has a bad value" are different problems with different correct responses:

  REJECT     structural. Nothing downstream can be trusted, so nothing loads.
             missing required column, unexpected column, unparseable type,
             implausible date, duplicate PRIMARY KEY, required_when unmet.

  EXCEPTION  row-level content on a well-formed file. The file loads and the
             offending rows flow to the existing data-quality exceptions layer.
             min_value violations, non-primary-key unique violations.

The distinction exists because the product's differentiator is telling a client
WHICH of their records are wrong. A client with 4 bad rows in 5,000 must get
"here are your 4 bad records", not "file rejected". A duplicate primary key is
the exception to that: it corrupts every join and inflates every aggregate, so
it stays structural.

ERROR REPORTING
---------------
All violations are collected, each carrying the Excel-visible row number
(header = row 1, first data row = row 2) and a bilingual message built from
the canonical schema's name_en / name_ar. Rendering is capped at
MAX_RENDERED_VIOLATIONS with an "and N more" tail so a catastrophically wrong
file still returns a usable message.
"""
import datetime
import os

import polars as pl
import yaml

# Rendered detail cap per file (cycle 1b-i ruling).
MAX_RENDERED_VIOLATIONS = 100

SEVERITY_REJECT = "reject"
SEVERITY_EXCEPTION = "exception"

# DATE plausible range (cycle 1b-i ruling): 1940-01-01 .. today + 2 years.
# The upper bound is deliberately in the future: an accepted offer with a start
# date next month is routine, so joining_date must accept future dates.
DEFAULT_MIN_DATE = datetime.date(1940, 1, 1)
DEFAULT_MAX_DATE_YEARS_AHEAD = 2

# Header occupies row 1 in the client's spreadsheet, so the first data row is 2.
FIRST_DATA_ROW = 2


class SchemaValidationError(ValueError):
    """Raised when a real CSV has at least one REJECT-severity violation."""

    def __init__(self, message, violations=None):
        super().__init__(message)
        self.violations = violations or []


class Violation(object):
    """One contract violation, localizable and row-addressable."""

    __slots__ = ("rule", "table", "column", "row", "value", "severity",
                 "message_en", "message_ar")

    def __init__(self, rule, table, column, severity, message_en, message_ar,
                 row=None, value=None):
        self.rule = rule
        self.table = table
        self.column = column
        self.severity = severity
        self.message_en = message_en
        self.message_ar = message_ar
        self.row = row
        self.value = value

    def message(self, locale="en"):
        return self.message_ar if locale == "ar" else self.message_en

    def as_dict(self):
        return {
            "rule": self.rule, "table": self.table, "column": self.column,
            "row": self.row, "value": self.value, "severity": self.severity,
            "message_en": self.message_en, "message_ar": self.message_ar,
        }

    def __repr__(self):
        return "<Violation {} {}.{} row={} {}>".format(
            self.severity, self.table, self.column, self.row, self.rule)


class ValidationResult(object):
    """Outcome of validating one file."""

    def __init__(self, table, csv_path, violations):
        self.table = table
        self.csv_path = csv_path
        self.violations = violations

    @property
    def rejects(self):
        return [v for v in self.violations if v.severity == SEVERITY_REJECT]

    @property
    def exceptions(self):
        return [v for v in self.violations if v.severity == SEVERITY_EXCEPTION]

    @property
    def ok(self):
        """True when nothing blocks the load. Exceptions do not block."""
        return not self.rejects

    def render(self, locale="en", limit=MAX_RENDERED_VIOLATIONS):
        lines = [v.message(locale) for v in self.violations[:limit]]
        extra = len(self.violations) - len(lines)
        if extra > 0:
            lines.append("and {} more".format(extra) if locale == "en"
                         else "و{} أخرى".format(extra))
        return "\n".join(lines)


# --------------------------------------------------------------------------
# contract access
# --------------------------------------------------------------------------

def _parse_expr(col, ctype):
    """Declared type -> a polars expression yielding null on parse failure."""
    t = str(ctype).upper()
    if t == "INTEGER":
        return pl.col(col).cast(pl.Int64, strict=False)
    if t == "DECIMAL":
        return pl.col(col).cast(pl.Float64, strict=False)
    if t == "DATE":
        return pl.col(col).str.to_date("%Y-%m-%d", strict=False)
    if t == "TIMESTAMP":
        return pl.col(col).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
    if t == "BOOLEAN":
        return (
            pl.when(pl.col(col).str.to_lowercase().is_in(["true", "false"]))
            .then(pl.col(col))
            .otherwise(None)
        )
    return None  # VARCHAR / unknown -> no parse check


def _load_contract(table, contracts_dir):
    path = os.path.join(contracts_dir, "{}_schema.yml".format(table))
    if not os.path.exists(path):
        raise SchemaValidationError(
            "[{}] no contract at {}; a real CSV cannot be ingested "
            "without a contract.".format(table, path)
        )
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    cols = spec.get("columns")
    if not cols:
        raise SchemaValidationError(
            "[{}] contract {} has no 'columns'.".format(table, path))
    return cols


def _labels(spec):
    """(en, ar) display labels for a column, falling back to its canonical name."""
    name = spec["name"]
    return spec.get("name_en") or name, spec.get("name_ar") or name


def _rows_for(mask_series):
    """Excel-visible row numbers for the True positions of a boolean series."""
    return [i + FIRST_DATA_ROW for i, flag in enumerate(mask_series) if flag]


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_csv(csv_path, table, contracts_dir="data/contracts", today=None):
    """Validate a CSV against its contract and return a ValidationResult.

    Collects every violation rather than raising on the first, so a client can
    fix a file in one pass. `today` is injectable purely so the DATE upper
    bound is deterministic under test.
    """
    columns = _load_contract(table, contracts_dir)
    contract_names = [c["name"] for c in columns]
    contract_set = set(contract_names)
    required = [c["name"] for c in columns if c.get("required")]
    by_name = {c["name"]: c for c in columns}
    today = today or datetime.date.today()
    max_date = datetime.date(today.year + DEFAULT_MAX_DATE_YEARS_AHEAD,
                             today.month, today.day)

    df = pl.read_csv(csv_path, infer_schema_length=0, null_values=[""])
    actual = list(df.columns)
    actual_set = set(actual)
    v = []

    # --- Rule 1: required columns present (structural) --------------------
    missing = [c for c in required if c not in actual_set]
    if missing:
        v.append(Violation(
            "required-columns", table, None, SEVERITY_REJECT,
            "[{}] missing required column(s) {}. Rule: required-columns. "
            "Expected columns: {}.".format(table, missing, contract_names),
            "[{}] أعمدة مطلوبة مفقودة {}. القاعدة: الأعمدة المطلوبة.".format(
                table, missing),
        ))

    # --- Rule 2: no unexpected columns (structural) -----------------------
    unexpected = [c for c in actual if c not in contract_set]
    if unexpected:
        v.append(Violation(
            "no-unexpected-columns", table, None, SEVERITY_REJECT,
            "[{}] unexpected column(s) {} not in contract. "
            "Rule: no-unexpected-columns. Allowed columns: {}.".format(
                table, unexpected, contract_names),
            "[{}] أعمدة غير متوقعة {} ليست في العقد. "
            "القاعدة: لا أعمدة غير متوقعة.".format(table, unexpected),
        ))

    # A structurally wrong file makes per-cell checks meaningless: the columns
    # are not the columns the contract describes. Report the shape problem
    # alone rather than burying it under hundreds of downstream complaints.
    if v:
        return ValidationResult(table, csv_path, v)

    for name in actual:
        spec = by_name[name]
        en, ar = _labels(spec)
        ctype = spec.get("type", "VARCHAR")

        # --- Rule 3: type conformance (structural) ------------------------
        expr = _parse_expr(name, ctype)
        if expr is not None:
            bad_mask = (pl.col(name).is_not_null() & expr.is_null())
            bad = df.select(bad_mask.sum().alias("n")).item()
            if bad and bad > 0:
                sample_bad = (df.filter(bad_mask).select(name).head(1).item())
                rows = _rows_for(df.select(bad_mask.alias("m"))["m"].to_list())
                v.append(Violation(
                    "type-conformance", table, name, SEVERITY_REJECT,
                    "{}: {} value(s) do not parse as {} (e.g. {!r}). "
                    "Rule: type-conformance.".format(en, bad, ctype, sample_bad),
                    "الصف {}، {}: القيمة {!r} لا تطابق النوع {}.".format(
                        rows[0] if rows else "?", ar, sample_bad, ctype),
                    row=rows[0] if rows else None, value=sample_bad,
                ))
                # A column that will not parse cannot be range-checked.
                continue

        # --- Rule 5: DATE plausible range (structural) --------------------
        # `0025-01-26` parses cleanly as year 25, so type conformance sees
        # nothing wrong. This is the corrupted Excel date serial named in
        # PRODUCT-ARCHITECTURE.md §4 and present in real client exports.
        if str(ctype).upper() in ("DATE", "TIMESTAMP"):
            lo = spec.get("min_date") or DEFAULT_MIN_DATE
            hi = spec.get("max_date") or max_date
            if isinstance(lo, str):
                lo = datetime.date.fromisoformat(lo)
            if isinstance(hi, str):
                hi = datetime.date.fromisoformat(hi)
            parsed = expr.cast(pl.Date) if expr is not None else None
            if parsed is not None:
                out_mask = (parsed.is_not_null()
                            & ((parsed < pl.lit(lo)) | (parsed > pl.lit(hi))))
                n_out = df.select(out_mask.sum().alias("n")).item()
                if n_out and n_out > 0:
                    flags = df.select(out_mask.alias("m"))["m"].to_list()
                    rows = _rows_for(flags)
                    bad_vals = df.filter(out_mask).select(name).to_series().to_list()
                    for r, val in list(zip(rows, bad_vals))[:MAX_RENDERED_VIOLATIONS]:
                        v.append(Violation(
                            "date-range", table, name, SEVERITY_REJECT,
                            "Row {}, {}: date {!r} is outside the plausible range "
                            "({} to {}). A year like 0025 usually means a corrupted "
                            "Excel date serial - check the source export.".format(
                                r, en, val, lo.isoformat(), hi.isoformat()),
                            "الصف {}، {}: التاريخ {!r} خارج النطاق المعقول "
                            "({} إلى {}). سنة مثل 0025 تعني عادةً تلفاً في تنسيق "
                            "التاريخ في ملف Excel - يرجى مراجعة الملف المصدر.".format(
                                r, ar, val, lo.isoformat(), hi.isoformat()),
                            row=r, value=val,
                        ))

        # --- Rule 6: min_value (EXCEPTION - row-level content) ------------
        # Not structural: a negative salary is one wrong row, and the product's
        # job is to say WHICH row. The file loads; the row is surfaced.
        if "min_value" in spec and str(ctype).upper() in ("INTEGER", "DECIMAL"):
            floor = spec["min_value"]
            num = expr
            low_mask = num.is_not_null() & (num < pl.lit(floor))
            n_low = df.select(low_mask.sum().alias("n")).item()
            if n_low and n_low > 0:
                flags = df.select(low_mask.alias("m"))["m"].to_list()
                rows = _rows_for(flags)
                vals = df.filter(low_mask).select(name).to_series().to_list()
                for r, val in list(zip(rows, vals))[:MAX_RENDERED_VIOLATIONS]:
                    v.append(Violation(
                        "min-value", table, name, SEVERITY_EXCEPTION,
                        "Row {}, {}: value {} is below the minimum of {}.".format(
                            r, en, val, floor),
                        "الصف {}، {}: القيمة {} أقل من الحد الأدنى {}.".format(
                            r, ar, val, floor),
                        row=r, value=val,
                    ))

        # --- Rule 7: unique -----------------------------------------------
        # Severity depends on whether the column is the primary key: a
        # duplicate PK corrupts every join and inflates every aggregate, so it
        # is structural. A duplicate elsewhere is a row-level exception.
        if spec.get("unique"):
            is_pk = bool(spec.get("primary_key"))
            sev = SEVERITY_REJECT if is_pk else SEVERITY_EXCEPTION
            col_vals = df.select(pl.col(name))[name].to_list()
            seen_at = {}
            for idx, val in enumerate(col_vals):
                if val is None or val == "":
                    continue
                seen_at.setdefault(val, []).append(idx + FIRST_DATA_ROW)
            dupes = {k: rws for k, rws in seen_at.items() if len(rws) > 1}
            for val in sorted(dupes)[:MAX_RENDERED_VIOLATIONS]:
                rws = dupes[val]
                v.append(Violation(
                    "unique-primary-key" if is_pk else "unique", table, name, sev,
                    "{}: value {!r} appears {} times (rows {}); it must be "
                    "unique.".format(en, val, len(rws), rws),
                    "{}: القيمة {!r} مكررة {} مرات (الصفوف {})؛ يجب أن تكون "
                    "فريدة.".format(ar, val, len(rws), rws),
                    row=rws[0], value=val,
                ))

        # --- Rule 4: allowed_values ---------------------------------------
        # Severity is declarable via `on_violation`. Default REJECT keeps a
        # legally or structurally fixed vocabulary hard (e.g. case_type, which
        # er_rules.sla_days keys on directly). A vocabulary we are confident of
        # but have not yet confirmed against real files declares
        # `on_violation: exception`, so an unexpected value surfaces as a data
        # quality exception instead of refusing the client's whole file. It can
        # be tightened to REJECT once real data confirms it.
        allowed = spec.get("allowed_values")
        if allowed:
            sev = (SEVERITY_EXCEPTION
                   if str(spec.get("on_violation", "")).lower() == "exception"
                   else SEVERITY_REJECT)
            allowed_set = set(allowed)
            seen = df.select(pl.col(name)).drop_nulls().unique().to_series().to_list()
            invalid = [x for x in seen if x not in allowed_set]
            if invalid:
                v.append(Violation(
                    "allowed-values", table, name, sev,
                    # No csv_path and no raw column name: this message is
                    # client-facing now that the upload UI renders it and puts
                    # it in a downloadable report. It used to embed the SERVER'S
                    # ABSOLUTE PATH to the staged file, which is both a leak of
                    # our filesystem layout and meaningless to the reader.
                    "{}: value(s) {} are not allowed. Allowed values: {}. "
                    "Rule: allowed-values.".format(en, invalid, allowed),
                    "{}: قيم غير مسموح بها {}. القيم المسموحة: {}.".format(
                        ar, invalid, allowed),
                    value=invalid[0] if invalid else None,
                ))

    # --- Rule 8: required_when (structural, conditional) ------------------
    # Declarative {column, equals} only - never an expression string. A
    # contract is operator-supplied data and must never be executable.
    for spec in columns:
        cond = spec.get("required_when")
        if not cond or spec["name"] not in actual_set:
            continue
        cond_col = cond.get("column")
        cond_val = cond.get("equals")
        name = spec["name"]
        en, ar = _labels(spec)
        if cond_col not in actual_set:
            v.append(Violation(
                "required-when-condition-missing", table, name, SEVERITY_REJECT,
                "{}: conditionally required on '{}', which is not present in "
                "the file. Rule: required-when.".format(en, cond_col),
                "{}: مطلوب شرطياً بناءً على '{}' غير الموجود في الملف.".format(
                    ar, cond_col),
            ))
            continue
        cond_en, cond_ar = _labels(by_name[cond_col])
        unmet = (pl.col(cond_col) == pl.lit(cond_val)) & (
            pl.col(name).is_null() | (pl.col(name).str.strip_chars() == pl.lit("")))
        n_unmet = df.select(unmet.sum().alias("n")).item()
        if n_unmet and n_unmet > 0:
            rows = _rows_for(df.select(unmet.alias("m"))["m"].to_list())
            for r in rows[:MAX_RENDERED_VIOLATIONS]:
                v.append(Violation(
                    "required-when", table, name, SEVERITY_REJECT,
                    "Row {}, {} is required when {} is \"{}\".".format(
                        r, en, cond_en, cond_val),
                    "الصف {}، {} مطلوب عندما تكون {} \"{}\".".format(
                        r, ar, cond_ar, cond_val),
                    row=r,
                ))

    return ValidationResult(table, csv_path, v)


def validate_csv_against_contract(csv_path, table,
                                  contracts_dir="data/contracts", today=None):
    """Backward-compatible gate: raise on the first REJECT-severity violation.

    Signature, exception type and message text are unchanged from Phase 0, so
    existing callers and the parity harness are unaffected.
    """
    result = validate_csv(csv_path, table, contracts_dir, today=today)
    if result.rejects:
        first = result.rejects[0]
        raise SchemaValidationError(first.message_en, result.violations)
    return None


# --------------------------------------------------------------------------
# presentation mapping: validator severity -> data-quality severity
# --------------------------------------------------------------------------

# base_command_center_exception_sources normalises severity with
#   CASE LOWER(TRIM(severity)) WHEN 'critical'/'warning'/'info' ... ELSE 'Unknown'
# so anything outside this set renders as 'Unknown' on the Command Center.
# The raw validator severities ('reject'/'exception') must NEVER be emitted.
DQ_SEVERITIES = ("Critical", "Warning", "Info")

# Pay columns: a negative amount is a payroll defect, not a nuance.
_PAY_COLUMNS = {"basic_salary", "gross_pay", "net_pay", "housing_allowance",
                "transport_allowance", "other_allowances", "overtime_amount",
                "deductions", "gosi_salary", "payroll_basic_salary"}


def dq_severity(violation):
    """Map a Violation to a Data Quality severity the marts understand."""
    if violation.rule == "min-value":
        return "Critical" if violation.column in _PAY_COLUMNS else "Warning"
    if violation.rule in ("unique", "unique-primary-key"):
        return "Warning"
    if violation.rule == "allowed-values":
        return "Warning"
    return "Warning"


def dq_recommended_action(violation, locale="en"):
    if locale == "ar":
        return "صحّح القيمة في الملف المصدر وأعد الرفع."
    return "Correct the value in the source file and re-upload."
