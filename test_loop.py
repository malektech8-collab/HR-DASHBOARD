import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")
for i in range(10):
    print(f"Iteration {i}...")
    r = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis;").fetchone()[0]
    print(f"  Result: {r}")
conn.close()
print("Done.")
