import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

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
