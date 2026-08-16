"""Mapping profiles (upload-mapping cycle A).

A real HR export does not match the canonical schema: Arabic headers with
inconsistent spacing, client-specific status vocabularies, columns the contract
has no home for, and derived fields absent from the source. Rule 2 rejects it
on the first upload, correctly, and a mapping profile is the sanctioned way to
reconcile it — recorded once, reused on every subsequent upload.

FOUR PROPERTIES, each load-bearing.

1. ROW-PRESERVING, WITH A BACK-MAP. Applying a profile renames and derives; it
   never filters, reorders or deduplicates. Every violation therefore still
   addresses the client's own row, and `source_column` lets the UI name the
   client's own header. Without this, a client reads "Row 47, Joining Date"
   about a canonical column they never wrote in a file they never made.

2. UPLOAD-TIME ONLY. The mapped file is canonical, lands in data/raw, and is
   revalidated by scripts/ingest_raw.py unchanged. Nothing downstream knows
   profiles exist, so this mechanism cannot become a second ingest path.

3. NO EVAL, EVER. A profile names a derivation RULE resolved through
   derivations.REGISTRY. It never carries an expression. A profile is
   operator-supplied data; treating it as code would make it an execution
   vector, and `load_profile` refuses anything expression-shaped rather than
   trusting that nobody will try.

4. NO CLIENT PII IN THE EVIDENCE. Profiles accumulate as training substrate for
   the AI column mapper, so what goes in them outlives the upload. Verbatim
   sample values are kept ONLY for columns whose canonical target declares
   `allowed_values` — there the values are a vocabulary and are the signal.
   Everywhere else the evidence is a redacted shape: dtype, cardinality, length
   range, pattern. A name or a salary adds nothing a model can use that the
   header does not already carry.

   PRODUCT-ARCHITECTURE §4 originally said to record "sample values" without
   qualification. That is corrected in the same cycle as this module.
"""
import datetime
import hashlib
import os
import re

import yaml

import canonical_schema as _cs
import derivations as _der
from text import normalise

PROFILE_DIR = os.path.join("data", "mapping")
CONTAINER_PROFILE_DIR = "/app/data/mapping"

# A profile is data. Anything that looks like it wants to be executed is
# refused outright rather than being carefully sandboxed.
_EXPRESSION_SHAPED = re.compile(
    r"(lambda\b|__|\beval\b|\bexec\b|\bimport\b|\bopen\s*\(|\bos\.|\bsys\.)")

# How many distinct values are worth keeping for a vocabulary column. A status
# column has a handful; anything larger is not a vocabulary and the cap stops a
# high-cardinality column sneaking through the enum branch.
MAX_VOCABULARY_SAMPLES = 25

NEWLINE = chr(10)

# What a value mapping into a REJECT enum DECIDES, in the client's terms.
#
# Carried here rather than in the UI copy because the consequence is a property
# of the contract, not of a screen: the CLI has to state it too, and so does the
# error raised when an affirmation is missing. A tick that says "confirm this
# mapping" asks nobody anything. A tick that says what the mapping decides is
# the only part of this mechanism that does any work.
VALUE_MAPPING_CONSEQUENCE = {
    "employees.status": (
        "Status decides who is counted as employed: headcount, Saudization "
        "and payroll exposure all read it.",
        "الحالة تحدد من يُحتسب موظفاً: عدد الموظفين والسعودة والتكلفة "
        "الشهرية جميعها تعتمد عليها."),
    "employees.end_of_service_type": (
        "End-of-service type decides whether a leaver is owed money. "
        "Article 80 is dismissal for cause and carries NO end-of-service "
        "award; Resignation and Articles 74/75/77/81 do. "
        "MAPPING TO `Unspecified` IS A DIFFERENT ASSERTION from the others: "
        "the article-bearing values assert WHICH entitlement applies, while "
        "`Unspecified` asserts that the source did not record the grounds and "
        "therefore NO entitlement can be derived. Choose it when the grounds "
        "are genuinely absent - never as a default for a value you have not "
        "looked up, because it withholds a figure the client may be owed.",
        "نوع نهاية الخدمة يحدد ما إذا كان للموظف المنتهية خدمته مستحقات. "
        "المادة 80 هي الفصل لسبب مشروع ولا تستوجب مكافأة نهاية خدمة، بخلاف "
        "الاستقالة والمواد 74 و75 و77 و81. أما الربط بقيمة `Unspecified` فهو "
        "إقرار مختلف: بأن النظام المصدر لم يسجّل السبب النظامي وأنه لا يمكن "
        "اشتقاق أي استحقاق منه. تُختار عند غياب السبب فعلياً، لا كقيمة "
        "افتراضية."),
    "employee_relations.case_type": (
        "Case type decides which cases appear as labour cases, and those are "
        "the ones reported as legal exposure.",
        "نوع القضية يحدد أي القضايا تظهر كقضايا عمالية، وهي التي يتم "
        "الإبلاغ عنها كتعرض قانوني."),
}


def consequence(table, column, locale="en"):
    """What mapping a value into this column decides, or None."""
    pair = VALUE_MAPPING_CONSEQUENCE.get("{}.{}".format(table, column))
    if not pair:
        return None
    return pair[1] if str(locale).lower().startswith("ar") else pair[0]


class MappingError(ValueError):
    """The profile is missing, malformed, or asks for something not allowed."""


def profile_dir():
    if os.path.isdir(os.path.dirname(CONTAINER_PROFILE_DIR)):
        return CONTAINER_PROFILE_DIR
    return PROFILE_DIR


def profile_path(table):
    return os.path.join(profile_dir(), "{}.yml".format(table))


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def _reject_expressions(node, where="profile"):
    """Walk the parsed YAML and refuse anything expression-shaped."""
    if isinstance(node, dict):
        for key, value in node.items():
            _reject_expressions(key, where)
            _reject_expressions(value, "{}.{}".format(where, key))
    elif isinstance(node, (list, tuple)):
        for item in node:
            _reject_expressions(item, where)
    elif isinstance(node, str):
        if _EXPRESSION_SHAPED.search(node):
            raise MappingError(
                "{}: value {!r} looks like an expression. A mapping profile is "
                "DATA. Derivations name a rule from the registry in "
                "scripts/derivations.py; they never carry code, because a "
                "profile is supplied by an operator and executing it would "
                "make a config file an execution vector.".format(where, node))


def load_profile(table, path=None, contracted=None):
    """The latest version of a table's profile, or None if there is none."""
    path = path or profile_path(table)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle) or {}
    _reject_expressions(spec, "profile[{}]".format(table))

    versions = spec.get("versions") or []
    if not versions:
        raise MappingError("{}: no versions recorded.".format(path))
    latest = max(versions, key=lambda v: int(v.get("version", 0)))
    _validate_targets(table, latest, contracted=contracted)
    # Also checked here, not only at the write: a profile that reached the disk
    # some other way must not be APPLIED unaffirmed.
    assert_value_mappings_confirmed(table, latest)
    return latest


def _validate_targets(table, version, contracted=None):
    """Every canonical target must exist on the contract. A typo that mapped to
    nothing would drop the column silently, which is the failure this whole
    mechanism exists to make impossible."""
    known = {c["name"] for c in _cs.columns(table)}
    unknown = sorted(set((version.get("columns") or {}).values()) - known)
    if unknown:
        hint = ""
        if "project" in unknown:
            # A profile written before 2026-08 maps to `project`, which no
            # longer exists on a fact table. Failing loudly is right; failing
            # loudly WITHOUT saying where it went would send an operator
            # hunting through a schema.
            hint = (" NOTE: `project` was renamed to `location` in 2026-08. "
                    "The column always held the physical site. The project a "
                    "site belongs to now lives in the separate `locations` "
                    "file, so map this column to `location` and upload a "
                    "locations file to get project-level figures back.")
        raise MappingError(
            "profile for '{}' maps to unknown canonical column(s) {}. "
            "Contract columns are {}.{}".format(
                table, unknown, sorted(known), hint))
    for target in (version.get("derive") or {}):
        if target not in known:
            raise MappingError(
                "profile for '{}' derives unknown column '{}'.".format(table, target))
    for target in (version.get("constants") or {}):
        if target not in known:
            raise MappingError(
                "profile for '{}' sets a constant for unknown column '{}'."
                .format(table, target))
        if target in _cs.required_columns(table):
            # A constant must be a CHOICE, not a workaround. Filling a required
            # column to get a file past the gate is the failure mode this
            # mechanism could become - the gate says the column is required,
            # and a constant makes it stop complaining. company, job_family and
            # cost_center were relaxed to optional precisely so that asserting
            # one is a decision rather than a way around the rejection.
            raise MappingError(
                "profile for '{}' sets a constant for '{}', which is REQUIRED. "
                "A constant must never be a way past the required-columns "
                "gate: either the client supplies the column, or the contract "
                "is wrong and relaxing it is a reviewed decision."
                .format(table, target))
    for target in (version.get("values") or {}):
        if target not in known:
            raise MappingError(
                "profile for '{}' maps values for unknown column '{}'."
                .format(table, target))
    for target, rule in (version.get("derive") or {}).items():
        # resolve() raises on anything not in the registry - no eval, and a new
        # rule is reviewed code rather than config
        _der.resolve(rule["rule"] if isinstance(rule, dict) else rule)
    return True


# --------------------------------------------------------------------------
# suggesting - rungs 1-5 of the ladder (cycle B, settled in cycle A's plan)
# --------------------------------------------------------------------------

ALIAS_PATH = os.path.join("config", "mapping_aliases.yml")

# rung -> (matched_by, confidence). Rungs 1-3 are derived from the contract
# itself and are pre-selected by the UI; rung 4 is a curated guess and is
# suggested only. A wrong HEADER mapping usually fails validation loudly, which
# is why pre-selection is acceptable here and is NOT acceptable for a value
# mapping into a REJECT enum - that one is silent, and needs a tick.
LADDER = [
    ("canonical", 1.0),
    ("label_exact", 0.95),
    ("label_normalised", 0.85),
    ("alias", 0.7),
]

_alias_cache = {}


def load_aliases(path=None):
    path = path or ALIAS_PATH
    if path in _alias_cache:
        return _alias_cache[path]
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    _alias_cache[path] = data
    return data


def suggest(table, headers, alias_path=None):
    """Ranked canonical candidates for each source header.

    Returns {header: [{"canonical", "matched_by", "confidence"}, ...]}, best
    first, empty list when nothing matched. Every rung records HOW it matched,
    because that is what makes the accumulated profiles trainable later - a
    mapping with no provenance teaches nothing.
    """
    columns = _cs.columns(table)
    by_key = {c["name"]: c["name"] for c in columns}
    by_label = {}
    by_label_normalised = {}
    for column in columns:
        for label in (column.get("name_ar"), column.get("name_en")):
            if not label:
                continue
            by_label.setdefault(label, column["name"])
            by_label_normalised.setdefault(normalise(label), column["name"])

    aliases = {}
    for canonical, spellings in (load_aliases(alias_path).get(table) or {}).items():
        for spelling in spellings or []:
            aliases.setdefault(normalise(spelling), canonical)

    out = {}
    for header in headers:
        key = normalise(header)
        rungs = [
            by_key.get(str(header).strip()),
            by_label.get(str(header).strip()),
            by_label_normalised.get(key),
            aliases.get(key),
        ]
        seen = set()
        candidates = []
        for (matched_by, confidence), canonical in zip(LADDER, rungs):
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            candidates.append({"canonical": canonical,
                               "matched_by": matched_by,
                               "confidence": confidence})
        out[header] = candidates
    return out


def header_fingerprint(headers):
    """Detects a changed export, so a stale profile is questioned rather than
    silently applied to a file it was not written for."""
    joined = "".join(sorted(str(h) for h in headers))
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# the PII rule
# --------------------------------------------------------------------------

def is_vocabulary_column(table, canonical):
    """True when the canonical target declares allowed_values.

    This is the whole PII rule in one predicate: a vocabulary's values ARE the
    training signal and are not personal data; a name's or a salary's are the
    opposite on both counts.
    """
    if not canonical:
        return False
    for column in _cs.columns(table):
        if column["name"] == canonical:
            return bool(column.get("allowed_values"))
    return False


def _pattern_of(values):
    """A coarse shape, not the value: digits -> 9, letters -> A."""
    if not values:
        return None
    shape = re.sub(r"\d", "9", re.sub(r"[^\W\d_]", "A", str(values[0]),
                                      flags=re.UNICODE))
    return shape[:32]


def value_profile(table, canonical, values):
    """Evidence for one source column, redacted unless it is a vocabulary.

    Returns a dict that is safe to persist. Nothing here may contain a
    client's personal data unless `is_vocabulary_column` is true.
    """
    present = [v for v in values if v not in (None, "")]
    if is_vocabulary_column(table, canonical):
        distinct = sorted({str(v) for v in present})
        return {
            "kind": "vocabulary",
            "distinct_values": distinct[:MAX_VOCABULARY_SAMPLES],
            "cardinality": len(distinct),
            "truncated": len(distinct) > MAX_VOCABULARY_SAMPLES,
        }
    lengths = [len(str(v)) for v in present]
    return {
        "kind": "redacted",
        "dtype": "empty" if not present else (
            "number" if all(_looks_numeric(v) for v in present) else "string"),
        "cardinality": len({str(v) for v in present}),
        "length_range": [min(lengths), max(lengths)] if lengths else None,
        "pattern": _pattern_of(present),
    }


def _looks_numeric(value):
    try:
        float(str(value).replace(",", ""))
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------
# applying a profile
# --------------------------------------------------------------------------

class MappingReport(object):
    """What applying a profile did, and what still needs a human."""

    def __init__(self):
        self.renamed = {}            # source header -> canonical
        self.ignored = []            # source headers dropped, by declaration
        self.unmapped = []           # source headers with no decision - BLOCKS
        self.derived = []            # canonical columns produced by a rule
        # canonical -> value ASSERTED by the operator for every row. Reported
        # separately from `renamed` on purpose: the client supplied one and an
        # operator asserted the other, and a reader must be able to tell.
        self.constants = {}
        self.value_mapped = {}       # canonical -> {source value: canonical}
        self.unmapped_values = {}    # canonical -> [values with no mapping]
        self.row_count = 0

    @property
    def back_map(self):
        """canonical column -> the client's own header. Violations use this so
        a client is never shown a column name they did not write."""
        return {canonical: source for source, canonical in self.renamed.items()}

    def as_dict(self):
        return {
            "renamed": dict(self.renamed),
            "ignored": list(self.ignored),
            "unmapped": list(self.unmapped),
            "derived": list(self.derived),
            "constants": dict(self.constants),
            "unmapped_values": {k: sorted(v) for k, v in self.unmapped_values.items()},
            "row_count": self.row_count,
            "back_map": self.back_map,
        }


def apply_profile(frame, table, version):
    """Rename, map values and derive. Returns (mapped_frame, MappingReport).

    ROW-PRESERVING by construction: this function only ever renames columns,
    replaces cell values within a column, and appends derived columns. There is
    no filter, no sort and no dedupe anywhere in it, and a test asserts the row
    count and row identity survive.
    """
    import polars as pl

    report = MappingReport()
    report.row_count = frame.height

    columns = (version.get("columns") or {})
    ignored = {entry["header"] if isinstance(entry, dict) else entry
               for entry in (version.get("ignored") or [])}

    # normalised lookup so a trailing space or an alef variant in the header
    # does not defeat a mapping the operator already made
    by_normalised = {normalise(source): (source, canonical)
                     for source, canonical in columns.items()}
    ignored_normalised = {normalise(h) for h in ignored}

    rename = {}
    drop = []
    for header in frame.columns:
        key = normalise(header)
        if key in by_normalised:
            _source, canonical = by_normalised[key]
            rename[header] = canonical
            report.renamed[header] = canonical
        elif key in ignored_normalised:
            drop.append(header)
            report.ignored.append(header)
        else:
            report.unmapped.append(header)

    mapped = frame.drop(drop).rename(rename)

    # value vocabularies, compared after normalisation so "نشط " and "نشط"
    # need one entry rather than two
    for canonical, pairs in (version.get("values") or {}).items():
        if canonical not in mapped.columns:
            continue
        lookup = {normalise(k): v for k, v in pairs.items()}
        report.value_mapped[canonical] = dict(pairs)
        column = mapped[canonical].to_list()
        translated, unmapped = [], set()
        allowed = _allowed_values(table, canonical)
        for value in column:
            if value in (None, ""):
                translated.append(value)
                continue
            key = normalise(value)
            if key in lookup:
                translated.append(lookup[key])
            else:
                translated.append(value)
                if allowed and str(value) not in allowed:
                    unmapped.add(str(value))
        mapped = mapped.with_columns(pl.Series(canonical, translated))
        if unmapped:
            report.unmapped_values[canonical] = unmapped

    # constants: a fact the OPERATOR asserts about every row.
    #
    # Applied after renaming and before derivation, so a derived column can
    # read one. A constant is invisible afterwards - once written, the column
    # looks exactly like one the client supplied, and nothing downstream can
    # tell the difference. That is why it carries `asserted_by` and a `basis`
    # (enforced at the write, see assert_constants_attributed) and why it is
    # recorded in evidence.
    #
    # It NEVER overwrites a mapped column: a constant is a choice for a column
    # the client does not have, not a way to override one they do.
    for canonical, spec in (version.get("constants") or {}).items():
        if canonical in mapped.columns:
            raise MappingError(
                "constants.{0}: that column is already mapped from the "
                "client's file. A constant asserts a value for a column they "
                "do NOT have; it must never silently replace real data. "
                "Remove the constant, or remove {0} from `columns`."
                .format(canonical))
        value = spec["value"] if isinstance(spec, dict) else spec
        mapped = mapped.with_columns(
            pl.lit(value).alias(canonical))
        report.constants[canonical] = value

    # derivations: the profile names a rule and a SOURCE header; the rule is
    # resolved from the registry, never evaluated
    for canonical, spec in (version.get("derive") or {}).items():
        rule = spec["rule"] if isinstance(spec, dict) else spec
        source = spec.get("from") if isinstance(spec, dict) else None
        if canonical in mapped.columns:
            continue
        if source is None or source not in frame.columns:
            raise MappingError(
                "derive.{}: source column {!r} is not in the uploaded file."
                .format(canonical, source))
        produced = _der.resolve(rule)(frame[source].to_list())
        mapped = mapped.with_columns(pl.Series(canonical, produced))
        report.derived.append(canonical)

    assert mapped.height == report.row_count, "apply_profile must preserve rows"
    return mapped, report


def _allowed_values(table, canonical):
    for column in _cs.columns(table):
        if column["name"] == canonical:
            return set(column.get("allowed_values") or [])
    return set()


def reject_enum_columns(table):
    """Canonical columns where an unmapped value BLOCKS the upload.

    Three today. The distinction matters to the UI: for these, an unmapped
    value is a mapping task with the canonical options listed - never a bare
    rejection that sends a client back to Excel to rename a word the product
    could learn once.
    """
    out = {}
    for column in _cs.columns(table):
        allowed = column.get("allowed_values")
        if not allowed:
            continue
        if str(column.get("on_violation", "")).lower() != "exception":
            out[column["name"]] = list(allowed)
    return out


# --------------------------------------------------------------------------
# writing a profile
# --------------------------------------------------------------------------

def constant_needs_affirmation(table, canonical):
    """Does asserting a constant for this column need a human tick?

    THE RULE, not a list: affirm wherever being wrong is NOT VISIBLE on the
    screen the client looks at.

      free text (company, cost_center, job_family)  -> NO
          Wrong is loud. Every row reads the same wrong company name, on
          screen, and the client says so immediately.

      any column with allowed_values                -> YES
          Same silence as a value mapping into a gated enum. A constant
          `status: Active` marks every leaver active and nothing looks odd.

      location                                      -> YES
          Free text, and the exception that proves the rule is about
          VISIBILITY rather than type. `location` feeds the locations join, so
          a constant location for a multi-site client renders as a clean
          single-site chart - confident, wrong, and indistinguishable from a
          client who genuinely has one site.
    """
    if _allowed_values(table, canonical):
        return True
    return canonical == "location"


def assert_constants_attributed(table, version):
    """A constant is an ASSERTION about the client, so it is signed and based.

    A value mapping asserts "this client's word means that canonical value". A
    constant asserts "this fact is true of every employee in this file" - a
    claim about their organisational structure, applied to every row, and
    INVISIBLE afterwards: the column ends up looking exactly like one they
    supplied.

    So it takes the same controls as a value mapping, and one more:

      asserted_by   who is making the claim. A record, not an authentication.
      basis         WHY it is true. Enforced as non-empty, which is all that
                    can be enforced - "single legal entity, confirmed with the
                    HR manager" is reviewable; a constant with no stated basis
                    is a guess someone will later mistake for data.
      affirmation   for columns where being wrong is invisible - see
                    constant_needs_affirmation().
    """
    problems = []
    confirmations = version.get("confirmations") or {}
    for canonical, spec in (version.get("constants") or {}).items():
        if not isinstance(spec, dict):
            problems.append(
                "  {}: must be a mapping with value / asserted_by / basis, "
                "not a bare value.".format(canonical))
            continue
        if not str(spec.get("asserted_by") or "").strip():
            problems.append(
                "  {}: no asserted_by. A constant is a claim about the "
                "client's organisation; an unsigned one is not reviewable."
                .format(canonical))
        if not str(spec.get("basis") or "").strip():
            problems.append(
                "  {}: no basis. State WHY this is true of every row - "
                "e.g. 'single legal entity, confirmed with the HR manager'. "
                "A constant with no basis is a guess that will later be "
                "mistaken for data.".format(canonical))
        if constant_needs_affirmation(table, canonical):
            record = confirmations.get(canonical) or {}
            if not str(record.get("confirmed_by") or "").strip():
                problems.append(
                    "  {}: needs an affirmation. Being wrong here would NOT "
                    "be visible on the client's screen - it renders as a "
                    "confident figure rather than an obvious error.".format(
                        canonical))
    if problems:
        raise MappingError(
            "refusing this mapping: a constant asserts a fact about EVERY row "
            "and is indistinguishable from client data once written."
            + NEWLINE + NEWLINE.join(problems)
            + NEWLINE +
            "تعذّر قبول الربط: القيمة الثابتة تُثبت واقعة على كل صف ولا يمكن "
            "تمييزها عن بيانات العميل بعد كتابتها.")
    return True


def assert_attributed(version):
    """Every version names who made it. Enforced at the write.

    A mapping is an assertion about what a client's data means, and it survives
    every upload after the one it was written for. Cycle A recorded `created_by`
    when it was supplied and accepted a version without it, so the decision that
    turns a client's word into a canonical one could be anonymous. This is a
    record, not an authentication - a console caller can still write anything -
    but an unsigned assertion is not reviewable at all.
    """
    who = str(version.get("created_by") or "").strip()
    if not who:
        raise MappingError(
            "refusing to save a mapping version with no 'created_by'. A value "
            "mapping decides what a client's data means and outlives the "
            "upload it was written for; an anonymous one cannot be reviewed."
            + NEWLINE +
            "لا يمكن حفظ إصدار ربط بدون 'created_by'. ربط القيم يحدد معنى "
            "بيانات العميل ويبقى بعد الرفع الذي كُتب من أجله.")
    return who


def assert_value_mappings_confirmed(table, version):
    """A value mapping into a REJECT enum needs a human affirmation.

    KEYED BY THE PAIR, NOT THE COLUMN. Confirming `status` today must not
    silently bless a pair added next month - that is the whole failure this
    prevents, and a column-level flag would wave it through.

    Called from BOTH save_version and load_profile. Save-side alone would leave
    the hand-written YAML path open, and hand-written YAML is exactly the path
    that produced the gap.

    Deliberately limited to the REJECT enums (three today). The EXCEPTION-enum
    columns are not gated: asking for fourteen affirmations would make the tick
    a formality, which is worse than not having one. Their mis-mapping remains
    an operator assertion the system accepts - see docs/phase-2/mapping-ui-plan
    §1.4, which is the honest residual, not an oversight.
    """
    gated = reject_enum_columns(table)
    confirmations = version.get("confirmations") or {}
    problems = []
    for canonical, pairs in (version.get("values") or {}).items():
        if canonical not in gated:
            continue
        record = confirmations.get(canonical) or {}
        who = str(record.get("confirmed_by") or "").strip()
        affirmed = record.get("pairs") or {}
        missing = {k: v for k, v in (pairs or {}).items() if affirmed.get(k) != v}
        if not who:
            problems.append((canonical, sorted((pairs or {}).items()),
                             "no confirmed_by"))
        elif missing:
            problems.append((canonical, sorted(missing.items()),
                             "not affirmed"))
    if not problems:
        return True

    lines = []
    for canonical, pairs, why in problems:
        shown = ", ".join("{!r} -> {!r}".format(k, v) for k, v in pairs)
        lines.append("  {} ({}): {}".format(canonical, why, shown))
        note = consequence(table, canonical)
        if note:
            lines.append("    {}".format(note))
    raise MappingError(
        "refusing this mapping: the value mapping(s) below rewrite a client's "
        "own words into canonical ones, and nobody has affirmed them."
        + NEWLINE + NEWLINE.join(lines) + NEWLINE +
        "Record the affirmation under confirmations.<column> with "
        "confirmed_by and the SAME pairs. Adding or changing a pair needs its "
        "own affirmation - a tick inherited from last month is not one."
        + NEWLINE +
        "تعذّر قبول الربط: القيم أدناه تعيد كتابة كلمات العميل إلى قيم "
        "معيارية دون تأكيد من مسؤول.")


def build_version(table, frame, decisions, created_by, values=None,
                  derive=None, confirmations=None, alias_path=None):
    """THE constructor for a profile version. Evidence by construction.

    Cycle A left evidence to discipline: `build_evidence()` then
    `save_version()`, and a hand-written YAML that skipped both loaded
    perfectly and captured nothing. Since the screen IS the data collection,
    that could not stay a matter of remembering - so this is the only sanctioned
    way to make a version, and `save_version` refuses one without the evidence
    it produces.

    `decisions` is {source header: {"decision": mapped|ignored|undecided,
    "chosen": canonical, "reason": why it was ignored}}. Everything else -
    matched_by, confidence, the candidates the human REJECTED, the fingerprint -
    is computed here rather than supplied, because a caller that has to
    remember to attach provenance is the failure this replaces.
    """
    headers = list(frame.columns)
    ranked = suggest(table, headers, alias_path=alias_path)

    columns, ignored, seed = {}, [], []
    for header in headers:
        decision = dict(decisions.get(header) or {})
        kind = decision.get("decision") or (
            "mapped" if decision.get("chosen") else "undecided")
        chosen = decision.get("chosen")
        candidates = ranked.get(header) or []

        matched_by, confidence = "human", None
        for candidate in candidates:
            if candidate["canonical"] == chosen:
                matched_by = candidate["matched_by"]
                confidence = candidate["confidence"]
                break
        # Everything the ladder offered and the human did not take. This is the
        # scarcest signal in the whole system and the only part that cannot be
        # reconstructed later: it says a candidate was PLAUSIBLE and WRONG.
        rejected = [c for c in candidates if c["canonical"] != chosen]

        if kind == "mapped" and chosen:
            columns[header] = chosen
        elif kind == "ignored":
            ignored.append({"header": header,
                            "reason": decision.get("reason")
                            or "No canonical home; ignored by the operator."})
        seed.append({"source_header": header, "matched_by": matched_by,
                     "confidence": confidence, "rejected": rejected})

    version = {
        "created_by": created_by,
        "columns": columns,
        "ignored": ignored,
        "values": dict(values or {}),
        "derive": dict(derive or {}),
        "confirmations": dict(confirmations or {}),
        "source_fingerprint": header_fingerprint(headers),
        "evidence": seed,
    }
    version["evidence"] = build_evidence(table, frame, version)
    return version


def assert_evidence_is_complete(version):
    """Every header the version acts on must carry evidence.

    Not a formality: without it a profile records WHAT was decided and nothing
    about how, and the accumulated profiles - the training substrate this whole
    format exists for - become a list of answers with the questions thrown away.
    """
    covered = {e.get("source_header") for e in (version.get("evidence") or [])}
    referenced = set(version.get("columns") or {})
    referenced |= {entry["header"] if isinstance(entry, dict) else entry
                   for entry in (version.get("ignored") or [])}
    missing = sorted(referenced - covered)
    if missing:
        raise MappingError(
            "refusing to save a mapping version with no evidence for {}. "
            "Build the version with mapping.build_version(), or the CLI at "
            "scripts/mapping_cli.py - both capture evidence by construction. "
            "A profile that records what was decided but not how teaches "
            "nothing later.".format(missing)
            + NEWLINE +
            "لا يمكن حفظ إصدار ربط بدون سجل للأعمدة: {}.".format(missing))
    return True


def save_version(table, version, path=None, contracted=None):
    """Append a version. Never mutate one.

    A client's export changes. If a profile mutated, nobody could say which
    mapping produced last month's numbers, and the accumulated evidence - the
    substrate the AI mapper learns from - would lose exactly the history that
    makes it valuable.
    """
    path = path or profile_path(table)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    spec = {"table": table, "versions": []}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            spec = yaml.safe_load(handle) or spec
    _reject_expressions(version, "new version")
    _validate_targets(table, version, contracted=contracted)
    assert_attributed(version)
    assert_value_mappings_confirmed(table, version)
    assert_constants_attributed(table, version)
    # PII is checked BEFORE completeness on purpose: "you tried to store a
    # client's names" must not be masked by "your evidence is incomplete".
    assert_no_pii(table, version)
    assert_evidence_is_complete(version)

    existing = spec.get("versions") or []
    version = dict(version)
    version["version"] = max([int(v.get("version", 0)) for v in existing] or [0]) + 1
    version.setdefault("created_at",
                       datetime.datetime.now().isoformat(timespec="seconds"))
    existing.append(version)
    spec["versions"] = existing
    spec["table"] = table
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(spec, handle, allow_unicode=True, sort_keys=False)
    return version


def assert_no_pii(table, version):
    """The PII rule, enforced at the write.

    A comment saying "do not put values here" is not a control. This refuses to
    persist verbatim values for any column whose canonical target does not
    declare allowed_values.
    """
    offenders = []
    for entry in (version.get("evidence") or []):
        profile = entry.get("value_profile") or {}
        canonical = entry.get("chosen")
        if profile.get("kind") == "vocabulary" and not is_vocabulary_column(
                table, canonical):
            offenders.append(entry.get("source_header"))
        if profile.get("kind") != "vocabulary" and "distinct_values" in profile:
            offenders.append(entry.get("source_header"))
    if offenders:
        raise MappingError(
            "refusing to store verbatim sample values for column(s) {} in the "
            "'{}' profile. Profiles accumulate as training substrate, so their "
            "contents outlive the upload; verbatim values are kept only where "
            "the canonical target declares allowed_values, because there they "
            "are a vocabulary rather than a person.".format(offenders, table))
    return True


def build_evidence(table, frame, version):
    """Evidence for every source header, with the PII rule already applied.

    Records the verbatim header, what it normalised to, what it was matched to
    and - the part that cannot be reconstructed later - the candidates a human
    REJECTED.
    """
    columns = version.get("columns") or {}
    ignored = {entry["header"] if isinstance(entry, dict) else entry
               for entry in (version.get("ignored") or [])}
    prior = {e.get("source_header"): e for e in (version.get("evidence") or [])}

    evidence = []
    for header in frame.columns:
        chosen = columns.get(header)
        existing = prior.get(header, {})
        evidence.append({
            "source_header": header,
            "normalised": normalise(header),
            "matched_by": existing.get("matched_by", "human"),
            "confidence": existing.get("confidence"),
            "chosen": chosen,
            # An explicit decision rather than a sentinel value. The first
            # version used "__ignored__", which tripped this module's own
            # no-expression guard on the dunder - a small illustration that a
            # magic string is not a data model.
            "decision": ("mapped" if chosen else
                         ("ignored" if header in ignored else "undecided")),
            "rejected": existing.get("rejected", []),
            "value_profile": value_profile(table, chosen,
                                           frame[header].to_list()),
        })
    return evidence
