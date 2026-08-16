import os
import sys
import duckdb
import yaml
import calendar
import json
import subprocess

# Load the repo-root .env BEFORE reading any env var, so a single uncommitted
# .env drives both this pipeline and the backend (no split-brain on DATA_MODE).
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

# Local dev layout: scripts/../backend/app. Containerized layout: backend contents
# are flattened directly under /app, so scripts/.. already contains the app package.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if not os.path.isdir(os.path.join(_backend_dir, "app")):
    _backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(_backend_dir)
# scripts/ on the path so the guard can import onboarding/canonical_schema
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.duckdb_client import configure_s3



def _cs_available_tables():
    import canonical_schema
    return canonical_schema.available_tables()


PROVENANCE_REGISTRY = "config/metric_provenance.yml"


def _write_domain_provenance(conn, data_mode):
    """Record, per domain, whether the CLIENT provided it. Read by the API.

    Four columns, and the distinction between the last two is the point:

      declared   the client said they are providing this domain
      row_count  what actually landed
      provided   whether the API may serve figures sourced from it

    In demo everything is provided, because sample data is the product being
    demonstrated. In real mode a contracted domain is provided iff it was
    DECLARED — never iff it has rows. The declared-domain guard has already
    made those agree or aborted, so reading declared here is not a shortcut;
    it is the reason a zero can be attributed to "not uploaded yet" rather
    than to a load that silently dropped every row.

    The 15 uncontracted tables are never provided in real mode. They have no
    contract, so they always load from data/sample — serving them beside real
    figures is the fabrication this whole step exists to stop.
    """
    with open(PROVENANCE_REGISTRY, "r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle) or {}
    domain_spec = spec.get("domains") or {}
    contracted = domain_spec.get("contracted") or {}
    uncontracted = domain_spec.get("uncontracted") or {}

    declared = set()
    coverage = {}
    history = {}
    if data_mode == "real":
        import onboarding as _onb
        declared = _onb.load_declared(contracted=set(_cs_available_tables()))
        coverage = _onb.load_coverage()
        history = _onb.load_history_depth()

    def count(table):
        try:
            return conn.execute("SELECT count(*) FROM {}".format(table)).fetchone()[0]
        except Exception:
            return 0

    # Category F: coverage_start/end say WHICH DAYS a date-grained domain
    # covers, and history_since how far back a point-in-time derivation may
    # reach. NULL in demo and for period-grained domains, which the readers
    # take to mean "the whole reporting period".
    rows = []
    for domain, tables in sorted(contracted.items()):
        window = coverage.get(domain)
        rows.append((domain, "contracted",
                     data_mode != "real" or domain in declared,
                     sum(count(t) for t in tables),
                     data_mode != "real" or domain in declared,
                     window[0] if window else None,
                     window[1] if window else None,
                     history.get(domain)))
    for domain, tables in sorted(uncontracted.items()):
        rows.append((domain, "uncontracted", False,
                     sum(count(t) for t in tables),
                     data_mode != "real", None, None, None))

    conn.execute("DROP TABLE IF EXISTS domain_provenance;")
    conn.execute("""
    CREATE TABLE domain_provenance (
        domain VARCHAR PRIMARY KEY,
        kind VARCHAR,
        declared BOOLEAN,
        row_count BIGINT,
        provided BOOLEAN,
        coverage_start DATE,
        coverage_end DATE,
        history_since DATE
    );
    """)
    conn.executemany(
        "INSERT INTO domain_provenance VALUES (?, ?, ?, ?, ?, ?, ?, ?);", rows)
    withheld = sorted(row[0] for row in rows if not row[4])
    print("Domain provenance written ({} domains, mode={}). Not provided: {}"
          .format(len(rows), data_mode, withheld or "none"))


def build_warehouse():
    os.makedirs("warehouse", exist_ok=True)
    db_path = "warehouse/hr_analytics.duckdb"
    
    print(f"Building DuckDB warehouse at {db_path}...")
    
    # Connect to DuckDB
    conn = duckdb.connect(db_path)
    configure_s3(conn)
    
    # Prepend DATA_PREFIX if configured
    data_prefix = os.getenv("DATA_PREFIX", "").rstrip("/")
    if data_prefix:
        data_prefix = f"{data_prefix}/"
        
    # 1. Create source tables from Parquet files
    parquet_files = {
        "employees": f"{data_prefix}data/silver/employees.parquet",
        "locations": f"{data_prefix}data/silver/locations.parquet",
        "payroll": f"{data_prefix}data/silver/payroll.parquet",
        "attendance": f"{data_prefix}data/silver/attendance.parquet",
        "hr_requests": f"{data_prefix}data/silver/hr_requests.parquet",
        "compliance": f"{data_prefix}data/silver/compliance.parquet",
        "employee_relations": f"{data_prefix}data/silver/employee_relations.parquet",
        "recruitment_requisitions": f"{data_prefix}data/silver/recruitment_requisitions.parquet",
        "candidates": f"{data_prefix}data/silver/candidates.parquet",
        "interviews": f"{data_prefix}data/silver/interviews.parquet",
        "offers": f"{data_prefix}data/silver/offers.parquet",
        "onboarding": f"{data_prefix}data/silver/onboarding.parquet",
        "workforce_plan": f"{data_prefix}data/silver/workforce_plan.parquet",
        "vacancy_requests": f"{data_prefix}data/silver/vacancy_requests.parquet",
        "data_quality": f"{data_prefix}data/gold/data_quality_report.parquet",
        # Milestone 2G: Talent, Performance, Learning & Succession
        "performance_reviews": f"{data_prefix}data/silver/performance_reviews.parquet",
        "performance_goals": f"{data_prefix}data/silver/performance_goals.parquet",
        "competency_assessments": f"{data_prefix}data/silver/competency_assessments.parquet",
        "learning_enrollments": f"{data_prefix}data/silver/learning_enrollments.parquet",
        "training_catalog": f"{data_prefix}data/silver/training_catalog.parquet",
        "succession_plans": f"{data_prefix}data/silver/succession_plans.parquet",
        "talent_reviews": f"{data_prefix}data/silver/talent_reviews.parquet",
        "employee_skills": f"{data_prefix}data/silver/employee_skills.parquet",
        "career_paths": f"{data_prefix}data/silver/career_paths.parquet",
    }

    
    for table_name, file_path in parquet_files.items():
        is_remote = file_path.startswith(("s3://", "http://", "https://"))
        if is_remote or os.path.exists(file_path):
            conn.execute(f"DROP TABLE IF EXISTS {table_name};")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{file_path}');")
            print(f"Loaded table '{table_name}' from {file_path}")
        else:
            print(f"Warning: file {file_path} not found. Skipping table '{table_name}'.")


    # Load business rules to get config context
    config_path = "config/business_rules.yml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f) or {}
    else:
        rules = {}

    # --- Cycle 5a: resolve report_month from the DATA (single source of truth) ---
    # Prefer payroll_period (the canonical, always-complete monthly HR close),
    # then compliance period. Returns None when neither is available — the
    # DECISION about what to do with that is not made here; it belongs to
    # report_period.resolve_report_month(), which fails closed in real mode
    # rather than reaching for a constant (Phase 2 P0-3, step 2a.5).
    def _derive_report_month():
        for query in (
            "SELECT CAST(MAX(payroll_period) AS VARCHAR) FROM payroll",
            "SELECT CAST(MAX(period) AS VARCHAR) FROM compliance",
        ):
            try:
                row = conn.execute(query).fetchone()
                if row and row[0]:
                    return str(row[0])[:7]
            except Exception:
                pass
        return None

    import report_period as _rp
    try:
        cc_report_month, cc_report_month_source = _rp.resolve_report_month(
            _derive_report_month())
    except _rp.ReportMonthError:
        # Abort BEFORE dbt, and close the connection first so the DuckDB file
        # is not left locked by a failed run.
        conn.close()
        raise
    year, month = map(int, cc_report_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    cc_report_month_end = f"{cc_report_month}-{last_day:02d}"
    cc_report_month_start = f"{cc_report_month}-01"
    # Item 5: talent period now tracks the same resolved month (drops the old
    # separate talent_report_month + hardcoded '-30' last-day bug) — see dbt_vars.

    # Trend anchors: the two months preceding the reporting period. dbt_project.yml
    # declared these as literals with a note saying they were "to be replaced by
    # report_month-relative derivation in the resolver cycle (5a)". That never
    # happened, so mart_exec_trends and mart_workforce_headcount_trend labelled
    # their history 2026-04 / 2026-05 whatever the client's period was — and
    # mart_exec_trends LEFT JOINs payroll on that label, so the cost silently
    # came back 0. Derived here from the one resolved period (step 2a.5).
    def _month_before(offset):
        index = year * 12 + (month - 1) - offset
        y, m = divmod(index, 12)
        m += 1
        return f"{y:04d}-{m:02d}", f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

    cc_trend_m1, cc_trend_m1_end = _month_before(2)
    cc_trend_m2, cc_trend_m2_end = _month_before(1)

    print(f"Resolved report_month: {cc_report_month} "
          f"({cc_report_month_start}..{cc_report_month_end}) "
          f"[source: {cc_report_month_source}]")
    print(f"Derived trend anchors: {cc_trend_m1}, {cc_trend_m2}")

    # --- Category F windows ------------------------------------------------
    # Attendance coverage: the days the client DECLARED they have reported.
    # Undeclared (and always in demo) it is the whole reporting period, which
    # is the pre-Category-F behaviour and keeps demo byte-identical.
    #
    # History depth: how far back a point-in-time headcount may reach. Real
    # mode with nothing declared resolves to the reporting period START, so
    # every historical trend month falls before it and renders NULL rather
    # than a derived-but-understated figure (ruling 2, as amended). Demo
    # resolves to a date before any sample record, so demo shows its history.
    cc_attendance_coverage_start = cc_report_month_start
    cc_attendance_coverage_end = cc_report_month_end
    cc_employees_history_since = "1900-01-01"
    if os.getenv("DATA_MODE", "demo") == "real":
        import onboarding as _onb_f
        _coverage = _onb_f.load_coverage().get("attendance")
        if _coverage:
            cc_attendance_coverage_start = _coverage[0].isoformat()
            cc_attendance_coverage_end = _coverage[1].isoformat()
        _history = _onb_f.load_history_depth().get("employees")
        cc_employees_history_since = (
            _history.isoformat() if _history else cc_report_month_start)
    print(f"Attendance coverage: {cc_attendance_coverage_start}"
          f"..{cc_attendance_coverage_end}")
    print(f"Employees history since: {cc_employees_history_since}")

    # Create placeholders for table-backed views to prevent dbt compilation errors
    conn.execute("""
    CREATE TABLE IF NOT EXISTS command_center_module_checks (
        module_key VARCHAR PRIMARY KEY,
        api_health_status VARCHAR,
        reconciliation_status VARCHAR,
        required_marts_present BOOLEAN,
        page_render_status VARCHAR,
        last_checked_at TIMESTAMP
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS command_center_overview_data (
        active_headcount INTEGER,
        payroll_cost DOUBLE,
        attendance_compliance_pct DOUBLE,
        saudization_pct DOUBLE,
        open_er_cases INTEGER,
        open_requisitions INTEGER,
        review_completion_pct DOUBLE,
        total_active_exceptions INTEGER,
        modules_healthy INTEGER,
        last_data_refresh TIMESTAMP,
        latest_source_business_date VARCHAR,
        data_quality_score DOUBLE
    );
    """)
    
    # --- Declared-domain guard (Phase 2 P0, step 1) -----------------------
    # Runs after ingest, before dbt. Real mode only: in demo nothing is
    # declared and everything is populated from sample, which would trip the
    # "populated but not declared" arm on every run.
    #
    # Making divergence fatal here is what lets the 11 dbt tests stay untouched.
    # An empty mart for an undeclared domain is provably "not uploaded yet"
    # rather than "silently broken", because declared-but-empty aborts before
    # dbt ever runs.
    if os.getenv("DATA_MODE", "demo") == "real":
        import onboarding as _onb
        contracted = set(_cs_available_tables())
        row_counts = {}
        for t in sorted(contracted):
            try:
                row_counts[t] = conn.execute(
                    f"SELECT count(*) FROM {t}").fetchone()[0]
            except Exception:
                row_counts[t] = 0
        _onb.assert_declared_matches_populated(row_counts)
        print(f"Declared-domain guard passed. Row counts: {row_counts}")

        # Declared-but-unsupported: history claimed deeper than the file can
        # back. Same failure shape as declared-but-empty, and just as silent
        # if allowed through — a trend chart would present months the file
        # cannot speak to.
        try:
            _earliest = conn.execute(
                "SELECT MIN(joining_date) FROM employees").fetchone()[0]
        except Exception:
            _earliest = None
        _onb.assert_history_supported("employees", _earliest)

    # --- Domain provenance for the API (Phase 2 P0-3, step 2b) ------------
    # The suppression layer has to answer "was this domain provided?" on every
    # request, and it must get the same answer the pipeline did. Writing it
    # here, into the warehouse the API already reads, keeps that to one source:
    # the API cannot see data/onboarding/ (different image, different volume),
    # and re-deriving provided-ness from row counts at request time would be
    # the inference this design has refused twice — a broken load and a domain
    # that was never uploaded are not the same thing.
    _write_domain_provenance(conn, os.getenv("DATA_MODE", "demo"))

    # Close connection so dbt doesn't lock the DuckDB file
    conn.close()

    # 2. Run dbt to build analytical views and tables programmatically
    print("Executing dbt run...")
    dbt_bin = os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "dbt.exe")
    if not os.path.exists(dbt_bin):
        dbt_bin = "dbt"

    # Column-grain provision, recorded at ingest. Imported here rather than at
    # module scope to match how the declared-domain guard above reaches it.
    import onboarding as _onb

    dbt_vars = {
        "data_mode": os.getenv("DATA_MODE", "demo"),
        "report_month": cc_report_month,
        "report_month_start": cc_report_month_start,
        "report_month_end": cc_report_month_end,
        # Item 2: anchor derives from the resolved period end (correct ER overdue math).
        "report_anchor_date": cc_report_month_end,
        # Item 5: talent period tracks the resolved month via the same monthrange end.
        "talent_month_start": cc_report_month_start,
        "talent_month_end": cc_report_month_end,
        # The attendance window. Same resolved period, no second idiom — these
        # ARE report_month_start/end, passed under the names the two attendance
        # models happen to read. Until step 2a.5 they were left at the
        # dbt_project.yml literals, so base_attendance_current filtered to June
        # 2026 and base_expected_attendance generated a June calendar no matter
        # what period the pipeline had just resolved. Unlike the payroll case
        # that needed no operator override to go wrong: any client whose payroll
        # close was not 2026-06 got a correct report_month and a June window.
        "start_date_str": cc_report_month_start,
        "end_date_str": cc_report_month_end,
        # Category F: the declared attendance coverage window, and how far
        # back a point-in-time headcount may legitimately reach.
        "attendance_coverage_start": cc_attendance_coverage_start,
        "attendance_coverage_end": cc_attendance_coverage_end,
        "employees_history_since": cc_employees_history_since,
        # Trend anchors, derived above from the same resolved period.
        "trend_m1": cc_trend_m1,
        "trend_m1_end": cc_trend_m1_end,
        "trend_m2": cc_trend_m2,
        "trend_m2_end": cc_trend_m2_end,
        "default_sla_days": rules.get("recruitment_rules", {}).get("default_sla_days", 45),
        "disciplinary_sla_days": rules.get("er_rules", {}).get("sla_days", {}).get("Disciplinary", 14),
        "grievance_sla_days": rules.get("er_rules", {}).get("sla_days", {}).get("Grievance", 10),
        "labor_case_sla_days": rules.get("er_rules", {}).get("sla_days", {}).get("Labor Case", 30),
        "grace_period_minutes": rules.get("attendance_rules", {}).get("grace_period_minutes", 15),
        "min_rating": rules.get("talent_rules", {}).get("min_rating_value", 1.0),
        "max_rating": rules.get("talent_rules", {}).get("max_rating_value", 5.0),
        "weekend_days_sql": ", ".join(f"'{day}'" for day in rules.get("attendance_rules", {}).get("weekend_days", ["Friday"])),
        "has_gosi_source_sql": "TRUE" if rules.get("compliance_rules", {}).get("has_gosi_source_for_period", True) else "FALSE",
        "has_wps_source_sql": "TRUE" if rules.get("compliance_rules", {}).get("has_wps_source_for_period", True) else "FALSE",
        # Column-grain provision, same idiom as the two above: does the CLIENT'S
        # FILE carry this column at all? Not "is it populated" - after
        # complete_canonical_shape() the column always exists and may be NULL,
        # so the data can no longer answer the question. A missing VALUE is a
        # data-quality exception; an ABSENT COLUMN is a coverage fact, and the
        # four cost-centre surfaces must not fire per employee for the second.
        "has_cost_center_source_sql": (
            "TRUE" if _onb.provides_column("employees", "cost_center")
            else "FALSE"),
        "critical_titles_sql": ", ".join(f"'{t}'" for t in rules.get("talent_rules", {}).get("critical_job_titles", []))
    }

    dbt_cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dbt_analytics"))

    dbt_run_cmd = [
        dbt_bin, "run",
        "--project-dir", ".",
        "--profiles-dir", ".",
        "--vars", json.dumps(dbt_vars)
    ]
    subprocess.run(dbt_run_cmd, check=True, cwd=dbt_cwd)
    print("dbt run completed successfully.")

    # 3. Run dbt test (Data Quality Gates)
    print("Executing dbt test...")
    dbt_test_cmd = [
        dbt_bin, "test",
        "--project-dir", ".",
        "--profiles-dir", ".",
        "--vars", json.dumps(dbt_vars)
    ]
    subprocess.run(dbt_test_cmd, check=True, cwd=dbt_cwd)
    print("dbt test completed successfully.")


    # Re-open connection for programmatic updates and reconciliation checks
    conn = duckdb.connect(db_path)

    print("Executing command center post-processing updates...")
    
    conn.execute("""
    INSERT INTO command_center_module_checks (module_key, api_health_status, reconciliation_status, required_marts_present, page_render_status, last_checked_at)
    SELECT module_key, 'Unknown', 'Unknown', FALSE, 'Unknown', CAST(NULL AS TIMESTAMP)
    FROM base_command_center_module_registry
    WHERE module_key NOT IN (SELECT module_key FROM command_center_module_checks);
    """)

    # Retrieve values in Python to avoid DuckDB query planning deadlocks
    cc_active_headcount = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
    cc_payroll_cost = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
    cc_attendance_compliance_pct = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
    cc_saudization_pct = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
    cc_open_er_cases = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
    cc_open_requisitions = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
    cc_review_completion_pct = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
    cc_total_active_exceptions = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
    cc_modules_healthy = conn.execute("SELECT COUNT(*) FROM mart_command_center_module_health WHERE status = 'Healthy'").fetchone()[0]
    cc_last_data_refresh = conn.execute("SELECT last_refresh_timestamp FROM base_command_center_report_context").fetchone()[0]
    cc_latest_source_business_date = conn.execute("SELECT MAX(max_source_date) FROM base_command_center_data_freshness").fetchone()[0]
    cc_data_quality_score = conn.execute("SELECT data_quality_score FROM mart_data_quality_summary").fetchone()[0]

    conn.execute("DELETE FROM command_center_overview_data;")
    conn.execute("""
    INSERT INTO command_center_overview_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (cc_active_headcount, cc_payroll_cost, cc_attendance_compliance_pct, cc_saudization_pct, cc_open_er_cases, cc_open_requisitions, cc_review_completion_pct, cc_total_active_exceptions, cc_modules_healthy, cc_last_data_refresh, cc_latest_source_business_date, cc_data_quality_score))

    # Reconciliation. Extracted to scripts/reconciliation.py in 2026-08.
    #
    # The eleven checks that used to live here compared the overview table
    # against the marts it had just been POPULATED FROM, fifteen lines above,
    # in this same connection. Eight of them could not fail. They now recompute
    # independently from the base models, and every one of them is tamper-
    # tested in backend/tests/test_reconciliation.py - the check is watched
    # failing before it is trusted to pass.
    import reconciliation
    print("Running Command Center integration reconciliation checks...")
    performed = reconciliation.run(conn)
    print("Command Center integration reconciliation checks PASSED "
          "({} independent checks).".format(performed))
    
    conn.close()
    print("DuckDB database warehouse creation complete.")

if __name__ == "__main__":
    build_warehouse()
