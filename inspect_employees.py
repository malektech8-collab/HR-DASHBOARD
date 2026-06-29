import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
desc = conn.execute("DESCRIBE employees;").fetchall()
cols = [d[0] for d in desc]
print(f"employees cols: {cols}")
conn.close()
