import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

try:
    print("Creating command_center_overview_data table...")
    conn.execute("""
    CREATE OR REPLACE TABLE command_center_overview_data (
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
    
    print("Retrieving values...")
    active_headcount = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
    print(f"  active_headcount: {active_headcount}")
    
    payroll_cost = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
    print(f"  payroll_cost: {payroll_cost}")
    
    attendance_compliance_pct = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
    print(f"  attendance_compliance_pct: {attendance_compliance_pct}")
    
    saudization_pct = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
    print(f"  saudization_pct: {saudization_pct}")
    
    open_er_cases = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
    print(f"  open_er_cases: {open_er_cases}")
    
    open_requisitions = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
    print(f"  open_requisitions: {open_requisitions}")
    
    review_completion_pct = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
    print(f"  review_completion_pct: {review_completion_pct}")
    
    total_active_exceptions = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
    print(f"  total_active_exceptions: {total_active_exceptions}")
    
    modules_healthy = conn.execute("SELECT COUNT(*) FROM mart_command_center_module_health WHERE status = 'Healthy'").fetchone()[0]
    print(f"  modules_healthy: {modules_healthy}")
    
    last_data_refresh = conn.execute("SELECT last_refresh_timestamp FROM base_command_center_report_context").fetchone()[0]
    print(f"  last_data_refresh: {last_data_refresh}")
    
    latest_source_business_date = conn.execute("SELECT MAX(max_source_date) FROM base_command_center_data_freshness").fetchone()[0]
    print(f"  latest_source_business_date: {latest_source_business_date}")
    
    data_quality_score = conn.execute("SELECT data_quality_score FROM mart_data_quality_summary").fetchone()[0]
    print(f"  data_quality_score: {data_quality_score}")
    
    print("Inserting values...")
    conn.execute("""
    INSERT INTO command_center_overview_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (active_headcount, payroll_cost, attendance_compliance_pct, saudization_pct, open_er_cases, open_requisitions, review_completion_pct, total_active_exceptions, modules_healthy, last_data_refresh, latest_source_business_date, data_quality_score))
    
    print("Creating mart_command_center_overview view...")
    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_overview AS
    SELECT * FROM command_center_overview_data;
    """)
    
    print("Querying mart_command_center_overview view...")
    r = conn.execute("SELECT * FROM mart_command_center_overview;").fetchall()
    print("Overview Row:", r)

except Exception as e:
    print("Error:", e)

conn.close()
print("Done.")
