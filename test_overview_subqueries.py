import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

subqueries = [
    ("mart_workforce_kpis", "SELECT active_headcount FROM mart_workforce_kpis"),
    ("mart_payroll_kpis", "SELECT total_payroll_cost FROM mart_payroll_kpis"),
    ("mart_attendance_kpis", "SELECT attendance_compliance_pct FROM mart_attendance_kpis"),
    ("mart_compliance_kpis", "SELECT saudization_pct FROM mart_compliance_kpis"),
    ("mart_er_kpis", "SELECT total_open_er_cases FROM mart_er_kpis"),
    ("mart_recruitment_kpis", "SELECT open_requisitions FROM mart_recruitment_kpis"),
    ("mart_talent_kpis", "SELECT review_completion_pct FROM mart_talent_kpis"),
    ("base_command_center_exception_sources", "SELECT COUNT(*) FROM base_command_center_exception_sources"),
    ("mart_command_center_module_health", "SELECT COUNT(*) FROM mart_command_center_module_health WHERE status = 'Healthy'"),
    ("base_command_center_report_context", "SELECT last_refresh_timestamp FROM base_command_center_report_context"),
    ("base_command_center_data_freshness", "SELECT MAX(max_source_date) FROM base_command_center_data_freshness"),
    ("mart_data_quality_summary", "SELECT data_quality_score FROM mart_data_quality_summary")
]

for name, q in subqueries:
    try:
        print(f"Running subquery for {name}: {q}")
        r = conn.execute(q).fetchone()
        print(f"  Result: {r}")
    except Exception as e:
        print(f"  ERROR for {name}: {e}")

conn.close()
print("Done.")
