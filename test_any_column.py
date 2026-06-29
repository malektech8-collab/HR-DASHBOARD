import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

try:
    print("Querying attendance_compliance_pct...")
    r = conn.execute("SELECT attendance_compliance_pct FROM mart_command_center_overview").fetchone()[0]
    print("  attendance_compliance_pct:", r)
except Exception as e:
    print("Error:", e)

conn.close()
print("Done.")
