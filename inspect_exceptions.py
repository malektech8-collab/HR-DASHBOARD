import duckdb

conn = duckdb.connect("warehouse/hr_analytics.duckdb")
marts = [
    "mart_data_quality_exceptions",
    "mart_workforce_exceptions",
    "mart_payroll_exceptions",
    "mart_attendance_exceptions",
    "mart_compliance_exceptions",
    "mart_er_exceptions",
    "mart_recruitment_exceptions",
    "mart_talent_exceptions"
]

for m in marts:
    try:
        desc = conn.execute(f"DESCRIBE {m};").fetchall()
        cols = [d[0] for d in desc]
        print(f"{m}: {cols}")
    except Exception as e:
        print(f"Error describing {m}: {e}")

conn.close()
