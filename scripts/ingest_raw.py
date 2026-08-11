import os
import sys
import polars as pl

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from validate_schema import (validate_csv, SchemaValidationError, dq_severity, dq_recommended_action,
                             SEVERITY_EXCEPTION)
from derivations import derive_column
import canonical_schema as _cs
import onboarding as _onb
import report_period as _rp

# Transport for EXCEPTION-severity contract violations: written here, merged
# into the gold DQ report by validate_data.py so they reach the Data Quality
# page. Gitignored; real-path only.
NEWLINE = chr(10)

# Sentinel directory for undeclared domains. It MUST NEVER EXIST ON DISK.
#
# In real mode an undeclared domain must ingest nothing, so its entry in the
# `files` map is pointed here. The per-table ingest blocks are all guarded by
# `os.path.exists(files[table])`, so a path that cannot exist makes them skip.
# The typed zero-row silver table is written afterwards, in the finalisation
# loop, where nothing can overwrite it.
#
# Naming it is deliberate. Control flow carried by a filesystem convention is
# exactly the `.uploaded` marker pattern — a trick that worked until someone
# created the file by accident and froze a table's ingest indefinitely. A named
# constant plus a test asserting the directory's absence makes this an
# invariant rather than a coincidence. If this directory is ever created, every
# undeclared domain would silently ingest whatever it contains.
UNDECLARED_SENTINEL_DIR = "data/raw/__undeclared__"


class OnboardingIncompleteError(RuntimeError):
    """Real mode cannot proceed: contracted domains are missing or undeclared."""


CONTRACT_EXCEPTIONS_PATH = "data/gold/contract_exceptions.parquet"
CONTRACT_EXCEPTION_SCHEMA = {
    "employee_id": pl.Utf8, "employee_name": pl.Utf8, "issue_type": pl.Utf8,
    "description": pl.Utf8, "severity": pl.Utf8, "recommended_action": pl.Utf8,
    "source": pl.Utf8, "source_table": pl.Utf8, "source_row": pl.Int64,
    "source_column": pl.Utf8, "rule": pl.Utf8,
}

def real_sourceable_tables():
    """Tables that may be loaded from real data (data/raw/) in data_mode='real'.

    DERIVED from data/contracts/, not hardcoded (cycle 1b-ii).

    Phase 0 Decision-1 ("Option A") required a table to be both NAMED here and
    contracted. That is SUPERSEDED: a contract is precisely the artifact that
    makes a table safe to real-source, because it is what the hard gate
    validates against. Keeping a second hand-maintained list meant a contract
    could exist that nothing could use — the gap employee_relations sat in, and
    the reason hr_requests stayed unreachable despite being contracted since
    Phase 0.

    The safety property is unchanged in substance but now has one owner: a
    table is real-sourceable IFF a contract exists to validate it. Authoring a
    contract is therefore the deliberate act that opens a real-data path, so
    the resolved set is printed on every real-mode run rather than left
    implicit.
    """
    return set(_cs.available_tables())



def _write_contract_exceptions(violations):
    """Persist EXCEPTION-severity violations for the data-quality layer.

    Shape matches the gold DQ report so they render alongside the existing
    checks. entity_id is left empty when a row cannot be attributed to an
    employee — an ID is never invented.
    """
    rows = []
    for v in violations:
        rows.append({
            "employee_id": "",
            "employee_name": "Unknown",
            "issue_type": "Contract: {}".format(v.rule),
            "description": v.message_en,
            "severity": dq_severity(v),
            "recommended_action": dq_recommended_action(v),
            "source": "contract",
            "source_table": v.table,
            "source_row": v.row,
            "source_column": v.column,
            "rule": v.rule,
        })
    pl.DataFrame(rows, schema=CONTRACT_EXCEPTION_SCHEMA).write_parquet(
        CONTRACT_EXCEPTIONS_PATH)
    print("[contract] wrote {} exception row(s) to {}".format(
        len(rows), CONTRACT_EXCEPTIONS_PATH))


# Domains whose models narrow to the reporting period, and the column that
# carries it. See report_period.assert_period_is_covered for what each one
# loses when its file does not cover that period.
PERIOD_COLUMNS = {
    "payroll": "payroll_period",
    "compliance": "period",
    "attendance": "attendance_date",
}


def _periods_in_csv(path, column, exists):
    """The period labels present in an uploaded file, or None if unreadable."""
    if not exists(path):
        return None
    try:
        frame = pl.read_csv(path, columns=[column])
    except Exception:
        # Column absent. In real mode the contract gate has already rejected
        # the file; there is nothing to compare here.
        return None
    return [v for v in frame[column].to_list() if v]


def resolve_ingest_report_month(files, exists=os.path.exists):
    """The period the pipeline WILL resolve, computed from the files at hand.

    build_warehouse resolves it after ingest, from silver. To gate at ingest we
    need it before, so this mirrors report_period's precedence exactly —
    operator, then payroll close, then compliance — over the same files that
    are about to become silver. Any divergence between this and the pipeline's
    resolution would make the gate test a period the marts do not use, which is
    why it reads the same columns in the same order rather than guessing.
    """
    operator = _rp.operator_report_month()
    if operator:
        return operator, _rp.SOURCE_OPERATOR
    for table, column in (("payroll", "payroll_period"), ("compliance", "period")):
        values = _periods_in_csv(files[table], column, exists) or []
        months = sorted({m for m in (_rp.normalise_month(v) for v in values) if m})
        if months:
            return months[-1], _rp.SOURCE_DATA
    return None, None


def check_period_coverage(files, exists=os.path.exists):
    """Every period-narrowed domain must cover the reporting period.

    Returns (month, source, checked-domains). A domain with no file, or an
    undeclared one pointing at the sentinel path, is skipped.

    Under pure derivation the payroll check is vacuous — the period IS payroll's
    latest close — and that is the point: the same rule covers the derivation
    and override cases without a special case for either. Compliance and
    attendance are NOT vacuous under derivation: the period comes from the
    payroll close, and nothing obliges a client's compliance or attendance file
    to be the same month.
    """
    month, source = resolve_ingest_report_month(files, exists=exists)
    if not month:
        return None, None, []
    checked = []
    for table in sorted(PERIOD_COLUMNS):
        values = _periods_in_csv(files[table], PERIOD_COLUMNS[table], exists)
        if values is None:
            continue
        _rp.assert_period_is_covered(values, month=month, source=table)
        checked.append(table)
    return month, source, checked


def check_payroll_period_matches_report_month(payroll_csv, exists=os.path.exists):
    """Reject an operator period the uploaded payroll file does not contain.

    Step 2a.5 replaced `payroll_period = (SELECT MAX(payroll_period) ...)` with
    `payroll_period = '{{ var("report_month") }}'` at every anchor site. Under
    derivation those are the same value by construction. Under an operator
    override they need not be, and the filter then matches NOTHING:

        payroll declared, payroll populated, silver correct,
        declared-domain guard green, dbt green, payroll cost 0.

    Every check passes and the number is a lie. So the disagreement is caught
    here, at ingest, with both periods named — never discovered downstream as
    an empty result. No operator period set means derivation is in charge, and
    derivation cannot disagree with itself.
    """
    month = _rp.operator_report_month()
    if not month or not exists(payroll_csv):
        return None
    try:
        periods = pl.read_csv(payroll_csv, columns=["payroll_period"])
    except Exception:
        # No payroll_period column. In real mode the contract gate has already
        # rejected the file; there is nothing to compare here.
        return None
    return _rp.assert_payroll_period_matches(
        periods["payroll_period"].to_list(), month=month)


def ingest(data_mode=None):
    if data_mode is None:
        data_mode = os.getenv("DATA_MODE", "demo")
    original_exists = os.path.exists
    def custom_exists(path):
        if isinstance(path, str) and path.startswith("data/sample/") and path.endswith("_sample.csv"):
            filename = os.path.basename(path)
            table_name = filename.replace("_sample.csv", "")
            marker1 = f"data/silver/{table_name}.parquet.uploaded"
            marker2 = f"/app/data/silver/{table_name}.parquet.uploaded"
            if original_exists(marker1) or original_exists(marker2):
                print(f"Skipping ingestion for table '{table_name}' due to manual upload (.uploaded marker).")
                return False
        return original_exists(path)
    os.path.exists = custom_exists

    os.makedirs("data/bronze", exist_ok=True)
    os.makedirs("data/silver", exist_ok=True)
    
    print("Starting data ingestion...")

    # Define paths
    files = {
        "employees": "data/sample/employees_sample.csv",
        "payroll": "data/sample/payroll_sample.csv",
        "attendance": "data/sample/attendance_sample.csv",
        "hr_requests": "data/sample/hr_requests_sample.csv",
        "compliance": "data/sample/compliance_sample.csv",
        "employee_relations": "data/sample/employee_relations_sample.csv",
        "recruitment_requisitions": "data/sample/recruitment_requisitions_sample.csv",
        "candidates": "data/sample/candidates_sample.csv",
        "interviews": "data/sample/interviews_sample.csv",
        "offers": "data/sample/offers_sample.csv",
        "onboarding": "data/sample/onboarding_sample.csv",
        "workforce_plan": "data/sample/workforce_plan_sample.csv",
        "vacancy_requests": "data/sample/vacancy_requests_sample.csv",
        "performance_reviews": "data/sample/performance_reviews_sample.csv",
        "performance_goals": "data/sample/performance_goals_sample.csv",
        "competency_assessments": "data/sample/competency_assessments_sample.csv",
        "learning_enrollments": "data/sample/learning_enrollments_sample.csv",
        "training_catalog": "data/sample/training_catalog_sample.csv",
        "succession_plans": "data/sample/succession_plans_sample.csv",
        "talent_reviews": "data/sample/talent_reviews_sample.csv",
        "employee_skills": "data/sample/employee_skills_sample.csv",
        "career_paths": "data/sample/career_paths_sample.csv"
    }

    # --- Real-data resolver (Phase 0): prefer data/raw/{table}.csv in real mode ---
    # Only the 4 REAL_SOURCEABLE tables are eligible. In demo mode (or when no
    # data/raw/{table}.csv is present) every entry stays the sample path, so the
    # rest of this function — and CI — is byte-identical to before.
    #
    # Marker immunity is BY CONSTRUCTION, not an explicit bypass: the .uploaded
    # freeze in custom_exists() below only special-cases paths that both start
    # with "data/sample/" and end with "_sample.csv". A data/raw/{table}.csv path
    # matches neither, so os.path.exists() on it never consults a marker and the
    # raw file is always (re)ingested on every run.
    # STALENESS GUARD — unconditional, every run, every mode.
    # If this file is left behind, yesterday's exceptions reappear against data
    # that has since been fixed, and a demo run would inherit a previous real
    # run's exceptions. This is the .uploaded marker bug in a new costume: that
    # marker froze a table's ingest indefinitely and zeroed four Attendance
    # widgets. Clear first, then decide whether to write.
    os.makedirs("data/gold", exist_ok=True)
    if original_exists(CONTRACT_EXCEPTIONS_PATH):
        os.remove(CONTRACT_EXCEPTIONS_PATH)
        print(f"[contract] cleared stale {CONTRACT_EXCEPTIONS_PATH}")

    contract_exceptions = []
    empty_domains = []
    if data_mode == "real":
        real_sourceable = sorted(real_sourceable_tables())
        print(f"[real] contracted domains: {real_sourceable}")

        # FAIL-CLOSED (Phase 2 P0-1). In real mode a missing raw file must NEVER
        # be filled from data/sample — that produced a dashboard showing a
        # fabricated headcount of 19 and Saudization of 50.0 beside a client's
        # one real payroll figure, with no indicator. The fallback branch is
        # deleted, not softened: there is no configuration under which real mode
        # serves sample data for a contracted domain.
        declared = _onb.load_declared(contracted=set(real_sourceable))
        present = [t for t in real_sourceable
                   if original_exists(f"data/raw/{t}.csv")]

        if not declared:
            # No declaration: every contracted domain is required. Report ALL
            # missing at once — a client fixing one domain per run is the
            # friction this product exists to remove.
            missing = [t for t in real_sourceable if t not in present]
            if missing:
                raise OnboardingIncompleteError(
                    "Real-data mode requires a file for every contracted domain. "
                    f"Missing: {', '.join(missing)}. To onboard incrementally, "
                    f"declare the domains you are providing in "
                    f"{_onb.registry_path()}." + NEWLINE +
                    "يتطلب وضع البيانات الحقيقية ملفاً لكل نطاق متعاقد عليه. "
                    f"الملفات الناقصة: {'، '.join(missing)}. لبدء الإدخال "
                    f"التدريجي، عرّف النطاقات التي تقدمها في الملف "
                    f"{_onb.registry_path()}."
                )
            targets = real_sourceable
        else:
            # Declared partial onboarding. A declaration is a promise: a
            # declared domain with no file is an error, not a fallback.
            print(f"[real] declared domains: {sorted(declared)}")
            missing = [t for t in sorted(declared) if t not in present]
            if missing:
                raise OnboardingIncompleteError(
                    f"Declared domain(s) with no file: {', '.join(missing)}. "
                    f"Expected data/raw/<domain>.csv. Remove them from "
                    f"{_onb.registry_path()} or provide the file." + NEWLINE +
                    f"نطاقات معرّفة بدون ملف: {'، '.join(missing)}."
                )
            targets = sorted(declared)
            empty_domains = [t for t in real_sourceable if t not in declared]

        for table in targets:
            raw_path = f"data/raw/{table}.csv"
            # Hard schema gate. Any REJECT-severity violation raises and aborts
            # the whole run (fail-closed) — no partial load. EXCEPTION-severity
            # violations do not block: the file loads and the rows are routed to
            # the data-quality layer.
            result = validate_csv(raw_path, table)
            if result.rejects:
                raise SchemaValidationError(result.rejects[0].message_en,
                                            result.violations)
            contract_exceptions.extend(result.exceptions)
            files[table] = raw_path
            print(f"[real] {table}: ingesting from {raw_path} (contract-validated).")
            if result.exceptions:
                print(f"[contract] {table}: {len(result.exceptions)} "
                      f"exception-severity violation(s) -> data quality layer.")

        # Undeclared domains load NOTHING. Point the resolver at a path that
        # cannot exist so the per-table ingest blocks below skip them entirely
        # — leaving files[table] on the sample path would have those blocks
        # re-ingest sample data a few hundred lines later, which is precisely
        # the fallback this change removes. The typed zero-row tables are
        # written after those blocks, in _finalise_undeclared().
        for table in empty_domains:
            files[table] = f"{UNDECLARED_SENTINEL_DIR}/{table}.csv"

    # Reporting period vs every domain whose models narrow to it. Runs in BOTH
    # modes and after the contract gate, so `files[...]` already points at
    # whichever file will actually be ingested — or, for an undeclared domain,
    # at the sentinel path that cannot exist, which makes it a no-op.
    period, period_source, period_checked = check_period_coverage(
        files, exists=original_exists)
    if period:
        print(f"[report_month] period {period} [{period_source}] covered by: "
              f"{', '.join(period_checked) or 'no period-bearing domain'}.")

    if contract_exceptions:
        _write_contract_exceptions(contract_exceptions)

    # 1. Employees
    if os.path.exists(files["employees"]):
        # Save raw to bronze
        df_raw = pl.read_csv(files["employees"])
        df_raw.write_parquet("data/bronze/employees.parquet")
        
        # Clean and type cast for silver
        df = pl.read_csv(files["employees"], null_values=[""])
        # Derived column (cycle 1b-i): real HRIS exports carry `nationality`,
        # not `is_saudi`. Derive ONLY when the column is absent — a file that
        # supplies it is taken at its word, which is also why demo (whose
        # sample carries is_saudi) is unaffected. The rule is resolved from the
        # registry by name and raises on any nationality it does not recognise;
        # it never defaults to false, because this drives Saudization.
        if "is_saudi" not in df.columns:
            if "nationality" not in df.columns:
                raise ValueError(
                    "employees: neither 'is_saudi' nor 'nationality' is present; "
                    "is_saudi cannot be derived."
                )
            spec = next(c for c in _cs.columns("employees") if c["name"] == "is_saudi")
            derived = derive_column(spec, df["nationality"].to_list())
            df = df.with_columns(pl.Series("is_saudi", derived, dtype=pl.Boolean))
            print("[derive] employees.is_saudi derived from nationality "
                  f"({sum(1 for x in derived if x)} Saudi / {len(derived)} rows).")
        df = df.with_columns([
            pl.col("is_saudi").cast(pl.Boolean, strict=False),
            pl.col("joining_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("termination_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("contract_end_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("basic_salary").cast(pl.Float64, strict=False),
            pl.col("housing_allowance").cast(pl.Float64, strict=False),
            pl.col("transport_allowance").cast(pl.Float64, strict=False),
        ])
        df.write_parquet("data/silver/employees.parquet")
        print("Ingested employees to bronze/silver.")

    # 2. Payroll
    if os.path.exists(files["payroll"]):
        df_raw = pl.read_csv(files["payroll"])
        df_raw.write_parquet("data/bronze/payroll.parquet")
        
        df = pl.read_csv(files["payroll"], null_values=[""])
        numeric_cols = [
            "basic_salary", "housing_allowance", "transport_allowance", 
            "other_allowances", "overtime_amount", "deductions", 
            "gross_pay", "net_pay"
        ]
        df = df.with_columns([
            pl.col(c).cast(pl.Float64, strict=False) for c in numeric_cols
        ])
        df.write_parquet("data/silver/payroll.parquet")
        print("Ingested payroll to bronze/silver.")

    # 3. Attendance
    if os.path.exists(files["attendance"]):
        df_raw = pl.read_csv(files["attendance"])
        df_raw.write_parquet("data/bronze/attendance.parquet")
        
        df = pl.read_csv(files["attendance"], null_values=[""])
        df = df.with_columns([
            pl.col("attendance_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("scheduled_start").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("scheduled_end").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("actual_check_in").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("actual_check_out").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("late_minutes").cast(pl.Int64, strict=False),
            pl.col("excused_late_minutes").cast(pl.Int64, strict=False),
            pl.col("net_late_minutes").cast(pl.Int64, strict=False),
            pl.col("absence_days").cast(pl.Float64, strict=False),
            pl.col("overtime_hours").cast(pl.Float64, strict=False),
            pl.col("overtime_approved").cast(pl.Boolean, strict=False),
            pl.col("missing_punch_count").cast(pl.Int64, strict=False),
        ])
        df.write_parquet("data/silver/attendance.parquet")
        print("Ingested attendance to bronze/silver.")

    # 4. HR Requests
    if os.path.exists(files["hr_requests"]):
        df_raw = pl.read_csv(files["hr_requests"])
        df_raw.write_parquet("data/bronze/hr_requests.parquet")
        
        df = pl.read_csv(files["hr_requests"], null_values=[""])
        df = df.with_columns([
            pl.col("created_at").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("closed_at").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("sla_hours").cast(pl.Int64, strict=False),
            pl.col("actual_hours").cast(pl.Int64, strict=False),
            pl.col("sla_breached").cast(pl.Boolean, strict=False),
        ])
        df.write_parquet("data/silver/hr_requests.parquet")
        print("Ingested hr_requests to bronze/silver.")

    # 5. Compliance
    if os.path.exists(files["compliance"]):
        df_raw = pl.read_csv(files["compliance"])
        df_raw.write_parquet("data/bronze/compliance.parquet")
        
        df = pl.read_csv(files["compliance"], null_values=[""])
        df = df.with_columns([
            pl.col("contract_authenticated").cast(pl.Boolean, strict=False),
            pl.col("gosi_salary").cast(pl.Float64, strict=False),
            pl.col("payroll_basic_salary").cast(pl.Float64, strict=False),
            pl.col("work_permit_expiry").str.to_date("%Y-%m-%d", strict=False),
            pl.col("iqama_expiry").str.to_date("%Y-%m-%d", strict=False),
        ])
        df.write_parquet("data/silver/compliance.parquet")
        print("Ingested compliance to bronze/silver.")
        
    # 6. Employee Relations
    if "employee_relations" in files and os.path.exists(files["employee_relations"]):
        df_raw = pl.read_csv(files["employee_relations"])
        df_raw.write_parquet("data/bronze/employee_relations.parquet")
        
        df = pl.read_csv(files["employee_relations"], null_values=[""])
        df = df.with_columns([
            pl.col("created_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("target_due_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("closed_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("escalated").cast(pl.Boolean, strict=False),
        ])
        df.write_parquet("data/silver/employee_relations.parquet")
        print("Ingested employee_relations to bronze/silver.")

    # 7. Production mode source check
    import yaml
    production_mode = False
    try:
        if os.path.exists("config/business_rules.yml"):
            with open("config/business_rules.yml", "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
                recruitment_rules = rules.get("recruitment_rules", {})
                production_mode = recruitment_rules.get("production_mode", False)
    except Exception as e:
        print(f"Error loading business rules: {e}")

    recruitment_tables = [
        "recruitment_requisitions", "candidates", "interviews", "offers", 
        "onboarding", "workforce_plan", "vacancy_requests"
    ]
    for table in recruitment_tables:
        path = files.get(table)
        if production_mode:
            if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
                raise ValueError(f"PRODUCTION EXCEPTION: Core recruitment source table '{table}' is empty or unavailable.")

    # 8. Ingest Recruitment tables
    # Requisitions
    if os.path.exists(files["recruitment_requisitions"]):
        df_raw = pl.read_csv(files["recruitment_requisitions"])
        df_raw.write_parquet("data/bronze/recruitment_requisitions.parquet")
        df = pl.read_csv(files["recruitment_requisitions"], null_values=[""])
        df = df.with_columns([
            pl.col("approval_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("target_hire_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("closed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/recruitment_requisitions.parquet")
        print("Ingested recruitment_requisitions to bronze/silver.")

    # Candidates
    if os.path.exists(files["candidates"]):
        df_raw = pl.read_csv(files["candidates"])
        df_raw.write_parquet("data/bronze/candidates.parquet")
        df = pl.read_csv(files["candidates"], null_values=[""])
        df = df.with_columns([
            pl.col("applied_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/candidates.parquet")
        print("Ingested candidates to bronze/silver.")

    # Interviews
    if os.path.exists(files["interviews"]):
        df_raw = pl.read_csv(files["interviews"])
        df_raw.write_parquet("data/bronze/interviews.parquet")
        df = pl.read_csv(files["interviews"], null_values=[""])
        df = df.with_columns([
            pl.col("interview_date").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
        ])
        df.write_parquet("data/silver/interviews.parquet")
        print("Ingested interviews to bronze/silver.")

    # Offers
    if os.path.exists(files["offers"]):
        df_raw = pl.read_csv(files["offers"])
        df_raw.write_parquet("data/bronze/offers.parquet")
        df = pl.read_csv(files["offers"], null_values=[""])
        df = df.with_columns([
            pl.col("offer_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("salary").cast(pl.Float64, strict=False),
            pl.col("outcome_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/offers.parquet")
        print("Ingested offers to bronze/silver.")

    # Onboarding
    if os.path.exists(files["onboarding"]):
        df_raw = pl.read_csv(files["onboarding"])
        df_raw.write_parquet("data/bronze/onboarding.parquet")
        df = pl.read_csv(files["onboarding"], null_values=[""])
        df = df.with_columns([
            pl.col("start_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/onboarding.parquet")
        print("Ingested onboarding to bronze/silver.")

    # Workforce Plan
    if os.path.exists(files["workforce_plan"]):
        df_raw = pl.read_csv(files["workforce_plan"])
        df_raw.write_parquet("data/bronze/workforce_plan.parquet")
        df = pl.read_csv(files["workforce_plan"], null_values=[""])
        df = df.with_columns([
            pl.col("planned_headcount").cast(pl.Int64, strict=False)
        ])
        df.write_parquet("data/silver/workforce_plan.parquet")
        print("Ingested workforce_plan to bronze/silver.")

    # Vacancy Requests
    if os.path.exists(files["vacancy_requests"]):
        df_raw = pl.read_csv(files["vacancy_requests"])
        df_raw.write_parquet("data/bronze/vacancy_requests.parquet")
        df = pl.read_csv(files["vacancy_requests"], null_values=[""])
        df = df.with_columns([
            pl.col("quantity").cast(pl.Int64, strict=False),
            pl.col("approved_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/vacancy_requests.parquet")
        print("Ingested vacancy_requests to bronze/silver.")

    # Ingest Talent tables
    # Performance Reviews
    if os.path.exists(files["performance_reviews"]):
        df_raw = pl.read_csv(files["performance_reviews"])
        df_raw.write_parquet("data/bronze/performance_reviews.parquet")
        df = pl.read_csv(files["performance_reviews"], null_values=[""])
        df = df.with_columns([
            pl.col("rating").cast(pl.Float64, strict=False),
            pl.col("completed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/performance_reviews.parquet")
        print("Ingested performance_reviews to bronze/silver.")

    # Performance Goals
    if os.path.exists(files["performance_goals"]):
        df_raw = pl.read_csv(files["performance_goals"])
        df_raw.write_parquet("data/bronze/performance_goals.parquet")
        df = pl.read_csv(files["performance_goals"], null_values=[""])
        df = df.with_columns([
            pl.col("due_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("completed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/performance_goals.parquet")
        print("Ingested performance_goals to bronze/silver.")

    # Competency Assessments
    if os.path.exists(files["competency_assessments"]):
        df_raw = pl.read_csv(files["competency_assessments"])
        df_raw.write_parquet("data/bronze/competency_assessments.parquet")
        df = pl.read_csv(files["competency_assessments"], null_values=[""])
        df = df.with_columns([
            pl.col("required_score").cast(pl.Float64, strict=False),
            pl.col("actual_score").cast(pl.Float64, strict=False),
            pl.col("assessed_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/competency_assessments.parquet")
        print("Ingested competency_assessments to bronze/silver.")

    # Learning Enrollments
    if os.path.exists(files["learning_enrollments"]):
        df_raw = pl.read_csv(files["learning_enrollments"])
        df_raw.write_parquet("data/bronze/learning_enrollments.parquet")
        df = pl.read_csv(files["learning_enrollments"], null_values=[""])
        df = df.with_columns([
            pl.col("enrollment_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("completion_date").str.to_date("%Y-%m-%d", strict=False)
        ])
        df.write_parquet("data/silver/learning_enrollments.parquet")
        print("Ingested learning_enrollments to bronze/silver.")

    # Training Catalog
    if os.path.exists(files["training_catalog"]):
        df_raw = pl.read_csv(files["training_catalog"])
        df_raw.write_parquet("data/bronze/training_catalog.parquet")
        df = pl.read_csv(files["training_catalog"], null_values=[""])
        df = df.with_columns([
            pl.col("duration_hours").cast(pl.Float64, strict=False)
        ])
        df.write_parquet("data/silver/training_catalog.parquet")
        print("Ingested training_catalog to bronze/silver.")

    # Succession Plans
    if os.path.exists(files["succession_plans"]):
        df_raw = pl.read_csv(files["succession_plans"])
        df_raw.write_parquet("data/bronze/succession_plans.parquet")
        df = pl.read_csv(files["succession_plans"], null_values=[""])
        df = df.with_columns([
            pl.col("is_critical").cast(pl.Boolean, strict=False)
        ])
        df.write_parquet("data/silver/succession_plans.parquet")
        print("Ingested succession_plans to bronze/silver.")

    # Talent Reviews
    if os.path.exists(files["talent_reviews"]):
        df_raw = pl.read_csv(files["talent_reviews"])
        df_raw.write_parquet("data/bronze/talent_reviews.parquet")
        df = pl.read_csv(files["talent_reviews"], null_values=[""])
        df = df.with_columns([
            pl.col("performance_rating").cast(pl.Float64, strict=False)
        ])
        df.write_parquet("data/silver/talent_reviews.parquet")
        print("Ingested talent_reviews to bronze/silver.")

    # Employee Skills
    if os.path.exists(files["employee_skills"]):
        df_raw = pl.read_csv(files["employee_skills"])
        df_raw.write_parquet("data/bronze/employee_skills.parquet")
        df = pl.read_csv(files["employee_skills"], null_values=[""])
        df.write_parquet("data/silver/employee_skills.parquet")
        print("Ingested employee_skills to bronze/silver.")

    # Career Paths
    if os.path.exists(files["career_paths"]):
        df_raw = pl.read_csv(files["career_paths"])
        df_raw.write_parquet("data/bronze/career_paths.parquet")
        df = pl.read_csv(files["career_paths"], null_values=[""])
        df = df.with_columns([
            pl.col("readiness_months").cast(pl.Int64, strict=False)
        ])
        df.write_parquet("data/silver/career_paths.parquet")
        print("Ingested career_paths to bronze/silver.")

    print("Ingestion complete.")
    # Undeclared domains: typed zero-row silver tables, written every run so a
    # previous run's rows can never survive as this client's data. Written here,
    # after the per-table blocks, so nothing can overwrite them.
    for table in empty_domains:
        _onb.write_empty_table(table)
        print(f"[real] {table}: not declared; empty table written "
              f"(no sample fallback).")

    os.path.exists = original_exists

if __name__ == "__main__":
    ingest()
