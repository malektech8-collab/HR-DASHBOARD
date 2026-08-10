import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

# Recreate the cross-joined view to be sure
conn.execute("""
CREATE OR REPLACE VIEW mart_command_center_overview AS
SELECT 
    wf.active_headcount,
    pr.total_payroll_cost AS payroll_cost,
    att.attendance_compliance_pct,
    comp.saudization_pct,
    er.total_open_er_cases AS open_er_cases,
    rec.open_requisitions,
    tal.review_completion_pct,
    exc.total_active_exceptions,
    hlth.modules_healthy,
    ctx.last_refresh_timestamp AS last_data_refresh,
    fresh.latest_source_business_date,
    dq.data_quality_score
FROM 
    (SELECT COALESCE(active_headcount, 0) AS active_headcount FROM mart_workforce_kpis) wf,
    (SELECT COALESCE(total_payroll_cost, 0.0) AS total_payroll_cost FROM mart_payroll_kpis) pr,
    (SELECT COALESCE(attendance_compliance_pct, 0.0) AS attendance_compliance_pct FROM mart_attendance_kpis) att,
    (SELECT COALESCE(saudization_pct, 0.0) AS saudization_pct FROM mart_compliance_kpis) comp,
    (SELECT COALESCE(total_open_er_cases, 0) AS total_open_er_cases FROM mart_er_kpis) er,
    (SELECT COALESCE(open_requisitions, 0) AS open_requisitions FROM mart_recruitment_kpis) rec,
    (SELECT COALESCE(review_completion_pct, 0.0) AS review_completion_pct FROM mart_talent_kpis) tal,
    (SELECT COUNT(*) AS total_active_exceptions FROM base_command_center_exception_sources) exc,
    (SELECT COUNT(*) AS modules_healthy FROM mart_command_center_module_health WHERE status = 'Healthy') hlth,
    (SELECT last_refresh_timestamp FROM base_command_center_report_context) ctx,
    (SELECT MAX(max_source_date) AS latest_source_business_date FROM base_command_center_data_freshness) fresh,
    (SELECT COALESCE(data_quality_score, 0.0) AS data_quality_score FROM mart_data_quality_summary) dq;
""")
print("View recreated.")

columns = [
    "active_headcount",
    "payroll_cost",
    "attendance_compliance_pct",
    "saudization_pct",
    "open_er_cases",
    "open_requisitions",
    "review_completion_pct",
    "total_active_exceptions",
    "modules_healthy",
    "last_data_refresh",
    "latest_source_business_date",
    "data_quality_score"
]

for col in columns:
    try:
        print(f"Querying column: {col}...")
        r = conn.execute(f"SELECT {col} FROM mart_command_center_overview").fetchone()[0]
        print(f"  {col} value: {r}")
    except Exception as e:
        print(f"  ERROR {col}: {e}")

conn.close()
print("Done.")
