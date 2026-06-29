import os
import polars as pl

def validate():
    os.makedirs("data/gold", exist_ok=True)
    print("Starting data validation...")
    
    # Load silver files
    employees_path = "data/silver/employees.parquet"
    payroll_path = "data/silver/payroll.parquet"
    attendance_path = "data/silver/attendance.parquet"
    hr_requests_path = "data/silver/hr_requests.parquet"
    compliance_path = "data/silver/compliance.parquet"

    issues = []

    # Helper function to add issue
    def add_issue(emp_id, name, issue_type, desc, severity, action):
        issues.append({
            "employee_id": str(emp_id) if emp_id else "",
            "employee_name": str(name) if name else "Unknown",
            "issue_type": issue_type,
            "description": desc,
            "severity": severity,
            "recommended_action": action
        })

    # 1. Employees validation
    if os.path.exists(employees_path):
        df_emp = pl.read_parquet(employees_path)
        
        # Check Duplicate Employee ID
        dup_ids = df_emp.group_by("employee_id").count().filter(pl.col("count") > 1).select("employee_id")
        for r in dup_ids.iter_rows():
            emp_id = r[0]
            # Get names for this ID
            names = df_emp.filter(pl.col("employee_id") == emp_id).select("employee_name").to_series().to_list()
            add_issue(
                emp_id,
                ", ".join(names),
                "Duplicate Employee ID",
                f"Employee ID '{emp_id}' is duplicated {len(names)} times in master file.",
                "Critical",
                "Merge or delete duplicate employee record in ERP"
            )

        # Check Active employees checks (manager, project, salary)
        active_emps = df_emp.filter(pl.col("status") == "Active")
        
        # Missing Manager
        missing_mgr = active_emps.filter(pl.col("manager_id").is_null() | (pl.col("manager_id") == ""))
        for r in missing_mgr.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Missing Manager",
                "Active employee has no manager ID assigned.",
                "Warning",
                "Assign supervisor/manager in employee profile"
            )

        # Missing Project
        missing_proj = active_emps.filter(pl.col("project").is_null() | (pl.col("project") == ""))
        for r in missing_proj.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Missing Project",
                "Active employee has no project code assigned.",
                "Warning",
                "Assign cost project code in master profile"
            )

        # Missing Nationality
        missing_nat = df_emp.filter(pl.col("nationality").is_null() | (pl.col("nationality") == ""))
        for r in missing_nat.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Missing Nationality",
                "Employee has no nationality specified.",
                "Warning",
                "Update nationality field in employee record"
            )

        # Missing Cost Center
        missing_cc = df_emp.filter(pl.col("cost_center").is_null() | (pl.col("cost_center") == ""))
        for r in missing_cc.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Missing Cost Center",
                "Employee has no cost center assigned.",
                "Warning",
                "Assign financial cost center code in master profile"
            )

        # Active Employee with Missing Salary (0 or null basic salary)
        missing_sal = active_emps.filter(pl.col("basic_salary").is_null() | (pl.col("basic_salary") == 0))
        for r in missing_sal.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Active Employee with Missing Salary",
                "Active employee contract has basic salary recorded as 0 or missing.",
                "Critical",
                "Input basic salary details in contract record"
            )

        # Abnormal contract basic salary (negative)
        neg_sal = active_emps.filter(pl.col("basic_salary") < 0)
        for r in neg_sal.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Abnormal Payroll Value",
                f"Employee contract has negative basic salary: {r['basic_salary']}",
                "Critical",
                "Review contract salary figures for input errors"
            )

    # 2. Payroll validation
    if os.path.exists(payroll_path) and os.path.exists(employees_path):
        df_pay = pl.read_parquet(payroll_path)
        df_emp = pl.read_parquet(employees_path)
        
        # We join payroll with employees to check status
        # Since EMP005 has duplicate IDs, we drop duplicates from df_emp for lookup
        df_emp_unique = df_emp.unique(subset=["employee_id"])
        df_pay_status = df_pay.join(df_emp_unique, on="employee_id", how="left")
        
        # Check: Inactive employee with payroll record
        # Inactive means status is Terminated or Inactive (or status is null, which means not found in master)
        inactive_payroll = df_pay_status.filter(
            (pl.col("status").is_in(["Terminated", "Inactive"])) | (pl.col("status").is_null())
        )
        for r in inactive_payroll.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"] if r["employee_name"] else "Unknown Employee",
                "Inactive Employee with Payroll Record",
                f"Employee status is '{r['status']}' but has active payroll run record for period {r['payroll_period']}.",
                "Critical",
                "Hold payroll run and check termination status/period logic"
            )

        # Check: Negative or abnormal payroll values (gross_pay < 0 or net_pay < 0 or basic_salary < 0)
        abnormal_pay = df_pay.filter(
            (pl.col("gross_pay") < 0) | (pl.col("net_pay") < 0) | (pl.col("basic_salary") < 0)
        )
        for r in abnormal_pay.iter_rows(named=True):
            emp_name = df_emp_unique.filter(pl.col("employee_id") == r["employee_id"]).select("employee_name").to_series().to_list()
            name = emp_name[0] if emp_name else "Unknown"
            add_issue(
                r["employee_id"],
                name,
                "Negative or Abnormal Payroll Value",
                f"Payroll record has negative/abnormal monetary values: Gross {r['gross_pay']}, Net {r['net_pay']}.",
                "Critical",
                "Review monthly payroll worksheet calculations for adjustments"
            )

    # 3. Attendance validation
    if os.path.exists(attendance_path) and os.path.exists(employees_path):
        df_att = pl.read_parquet(attendance_path)
        df_emp = pl.read_parquet(employees_path)
        df_emp_unique = df_emp.unique(subset=["employee_id"])
        
        # Check: Missing punches
        missing_punch = df_att.filter(pl.col("missing_punch_count") > 0)
        for r in missing_punch.iter_rows(named=True):
            emp_name = df_emp_unique.filter(pl.col("employee_id") == r["employee_id"]).select("employee_name").to_series().to_list()
            name = emp_name[0] if emp_name else "Unknown"
            add_issue(
                r["employee_id"],
                name,
                "Attendance Record with Missing Punch",
                f"Missing punch registered on {r['attendance_date'].strftime('%Y-%m-%d')}.",
                "Warning",
                "Request employee punch reconciliation or supervisor approval"
            )

    # 4. HR Requests validation
    if os.path.exists(hr_requests_path) and os.path.exists(employees_path):
        df_req = pl.read_parquet(hr_requests_path)
        df_emp = pl.read_parquet(employees_path)
        df_emp_unique = df_emp.unique(subset=["employee_id"])
        
        # Check: SLA breached
        sla_breach = df_req.filter(pl.col("sla_breached") == True)
        for r in sla_breach.iter_rows(named=True):
            emp_name = df_emp_unique.filter(pl.col("employee_id") == r["employee_id"]).select("employee_name").to_series().to_list()
            name = emp_name[0] if emp_name else "Unknown"
            add_issue(
                r["employee_id"],
                name,
                "HR Request Breaching SLA",
                f"HR Request {r['request_id']} of type '{r['request_type']}' exceeded SLA: Actual {r['actual_hours']} hrs, SLA {r['sla_hours']} hrs.",
                "Warning",
                "Escalate request status and allocate to alternate agent"
            )

    # Write gold output
    if len(issues) > 0:
        df_gold = pl.DataFrame(issues)
    else:
        # Create empty with proper schema
        df_gold = pl.DataFrame(
            schema={
                "employee_id": pl.Utf8,
                "employee_name": pl.Utf8,
                "issue_type": pl.Utf8,
                "description": pl.Utf8,
                "severity": pl.Utf8,
                "recommended_action": pl.Utf8
            }
        )

    df_gold.write_parquet("data/gold/data_quality_report.parquet")
    print(f"Validation complete. Generated {len(issues)} issues in data/gold/data_quality_report.parquet")

if __name__ == "__main__":
    validate()
