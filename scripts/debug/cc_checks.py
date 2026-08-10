import duckdb
conn = duckdb.connect("warehouse/hr_analytics.duckdb")
print("Connected.")

try:
    print("Check 1: Active Headcount")
    kpi_hc = conn.execute("SELECT active_headcount FROM mart_command_center_overview").fetchone()[0]
    ref_hc = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
    print(f"  kpi_hc: {kpi_hc}, ref_hc: {ref_hc}")

    print("Check 2: Payroll Cost")
    kpi_cost = conn.execute("SELECT payroll_cost FROM mart_command_center_overview").fetchone()[0]
    ref_cost = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
    print(f"  kpi_cost: {kpi_cost}, ref_cost: {ref_cost}")

    print("Check 3: Attendance Compliance")
    kpi_att = conn.execute("SELECT attendance_compliance_pct FROM mart_command_center_overview").fetchone()[0]
    ref_att = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
    print(f"  kpi_att: {kpi_att}, ref_att: {ref_att}")

    print("Check 4: Saudization")
    kpi_compliance = conn.execute("SELECT saudization_pct FROM mart_command_center_overview").fetchone()[0]
    ref_compliance = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
    print(f"  kpi_compliance: {kpi_compliance}, ref_compliance: {ref_compliance}")

    print("Check 5: ER Open Cases")
    kpi_er = conn.execute("SELECT open_er_cases FROM mart_command_center_overview").fetchone()[0]
    ref_er = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
    print(f"  kpi_er: {kpi_er}, ref_er: {ref_er}")

    print("Check 6: Recruitment Open Requisitions")
    kpi_req = conn.execute("SELECT open_requisitions FROM mart_command_center_overview").fetchone()[0]
    ref_req = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
    print(f"  kpi_req: {kpi_req}, ref_req: {ref_req}")

    print("Check 7: Review Completion")
    kpi_talent = conn.execute("SELECT review_completion_pct FROM mart_command_center_overview").fetchone()[0]
    ref_talent = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
    print(f"  kpi_talent: {kpi_talent}, ref_talent: {ref_talent}")

    print("Check 8: Total Active Exceptions")
    kpi_exc = conn.execute("SELECT total_active_exceptions FROM mart_command_center_overview").fetchone()[0]
    actual_exc = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
    print(f"  kpi_exc: {kpi_exc}, actual_exc: {actual_exc}")

    print("Check 9: Module Registry Count")
    reg_count = conn.execute("SELECT COUNT(*) FROM base_command_center_module_registry").fetchone()[0]
    print(f"  reg_count: {reg_count}")

    print("Check 10: Freshness Rows Count")
    fresh_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_data_freshness").fetchone()[0]
    print(f"  fresh_count: {fresh_count}")

    print("Check 11: Navigation Status Rows Count")
    nav_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_navigation_status").fetchone()[0]
    print(f"  nav_count: {nav_count}")

    print("All checks PASSED in diagnostic script.")
except Exception as e:
    print(f"FAILED: {e}")

conn.close()
print("Done.")
