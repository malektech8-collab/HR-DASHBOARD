import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

views = [
    "base_command_center_report_context",
    "base_command_center_module_registry",
    "base_command_exception_data_quality",
    "base_command_exception_workforce",
    "base_command_exception_payroll",
    "base_command_exception_attendance",
    "base_command_exception_compliance",
    "base_command_exception_er",
    "base_command_exception_recruitment",
    "base_command_exception_talent",
    "base_command_center_exception_sources",
    "base_command_center_data_freshness",
    "mart_command_center_data_freshness",
    "base_command_center_module_status",
    "mart_command_center_module_health",
    "mart_command_center_overview",
    "mart_command_center_priority_alerts",
    "mart_command_center_exception_summary",
    "mart_command_center_navigation_status",
    "mart_command_center_filter_options"
]

for v in views:
    try:
        print(f"Querying {v}...")
        r = conn.execute(f"SELECT * FROM {v};").fetchall()
        print(f"  OK: {len(r)} rows")
    except Exception as e:
        print(f"  ERROR {v}: {e}")

conn.close()
print("Done.")
