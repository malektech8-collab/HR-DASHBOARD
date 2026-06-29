import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")
try:
    print("Querying mart_payroll_kpis...")
    r = conn.execute("SELECT * FROM mart_payroll_kpis;").fetchall()
    print("Result:", r)
except Exception as e:
    print("Error:", e)
conn.close()
print("Done.")
