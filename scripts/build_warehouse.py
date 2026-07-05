import os
import sys
import duckdb
import yaml
import calendar
import json
import subprocess

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.db.duckdb_client import configure_s3



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

    cc_rules = rules.get("command_center_rules", {})
    cc_report_month = cc_rules.get("report_month", "2026-06")
    try:
        year, month = map(int, cc_report_month.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        cc_report_month_end = f"{cc_report_month}-{last_day:02d}"
    except Exception:
        cc_report_month_end = f"{cc_report_month}-30"
    cc_report_month_start = f"{cc_report_month}-01"

    talent_rules = rules.get("talent_rules", {})
    talent_report_month = talent_rules.get("default_report_month", "2026-06")

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
    
    # Close connection so dbt doesn't lock the DuckDB file
    conn.close()

    # 2. Run dbt to build analytical views and tables programmatically
    print("Executing dbt run...")
    dbt_bin = os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "dbt.exe")
    if not os.path.exists(dbt_bin):
        dbt_bin = "dbt"

    dbt_vars = {
        "report_month": cc_report_month,
        "report_month_start": cc_report_month_start,
        "report_month_end": cc_report_month_end,
        "report_anchor_date": cc_report_month_end,
        "talent_month_start": f"{talent_report_month}-01",
        "talent_month_end": f"{talent_report_month}-30",
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

    print("Running Command Center integration reconciliation checks...")
    
    # 1. Active Headcount
    kpi_hc = conn.execute("SELECT active_headcount FROM mart_command_center_overview").fetchone()[0]
    ref_hc = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
    if kpi_hc != ref_hc:
        raise ValueError(f"Command Center Active Headcount ({kpi_hc}) != Workforce Active Headcount ({ref_hc})")

    # 2. Payroll Cost
    kpi_pay = conn.execute("SELECT payroll_cost FROM mart_command_center_overview").fetchone()[0]
    ref_pay = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
    if abs(kpi_pay - ref_pay) > 0.01:
        raise ValueError(f"Command Center Payroll Cost ({kpi_pay}) != Payroll Cost ({ref_pay})")

    # 3. Attendance Compliance
    kpi_att = conn.execute("SELECT attendance_compliance_pct FROM mart_command_center_overview").fetchone()[0]
    ref_att = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
    if abs(kpi_att - ref_att) > 0.001:
        raise ValueError(f"Command Center Attendance Compliance ({kpi_att}) != Attendance Compliance ({ref_att})")

    # 4. Saudization %
    kpi_saudi = conn.execute("SELECT saudization_pct FROM mart_command_center_overview").fetchone()[0]
    ref_saudi = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
    if abs(kpi_saudi - ref_saudi) > 0.001:
        raise ValueError(f"Command Center Saudization ({kpi_saudi}) != Compliance Saudization ({ref_saudi})")

    # 5. Open ER Cases
    kpi_er = conn.execute("SELECT open_er_cases FROM mart_command_center_overview").fetchone()[0]
    ref_er = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
    if kpi_er != ref_er:
        raise ValueError(f"Command Center Open ER Cases ({kpi_er}) != ER Open Cases ({ref_er})")

    # 6. Open Requisitions
    kpi_req = conn.execute("SELECT open_requisitions FROM mart_command_center_overview").fetchone()[0]
    ref_req = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
    if kpi_req != ref_req:
        raise ValueError(f"Command Center Open Requisitions ({kpi_req}) != Recruitment Open Requisitions ({ref_req})")

    # 7. Review Completion %
    kpi_talent = conn.execute("SELECT review_completion_pct FROM mart_command_center_overview").fetchone()[0]
    ref_talent = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
    if abs(kpi_talent - ref_talent) > 0.001:
        raise ValueError(f"Command Center Review Completion ({kpi_talent}) != Talent Review Completion ({ref_talent})")

    # 8. Total Active Exceptions
    kpi_exc = conn.execute("SELECT total_active_exceptions FROM mart_command_center_overview").fetchone()[0]
    actual_exc = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
    if kpi_exc != actual_exc:
        raise ValueError(f"Command Center Total Active Exceptions ({kpi_exc}) != actual combined exceptions ({actual_exc})")

    # 9. Modules registry count = 9
    reg_count = conn.execute("SELECT COUNT(*) FROM base_command_center_module_registry").fetchone()[0]
    if reg_count != 9:
        raise ValueError(f"Command Center Module registry count ({reg_count}) != 9")

    # 10. Data freshness rows = 9
    fresh_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_data_freshness").fetchone()[0]
    if fresh_count != 9:
        raise ValueError(f"Command Center Freshness rows count ({fresh_count}) != 9")

    # 11. Navigation status rows = 9
    nav_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_navigation_status").fetchone()[0]
    if nav_count != 9:
        raise ValueError(f"Command Center Navigation status rows count ({nav_count}) != 9")

    print("Command Center integration reconciliation checks PASSED.")
    
    conn.close()
    print("DuckDB database warehouse creation complete.")

if __name__ == "__main__":
    build_warehouse()
