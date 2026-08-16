import os
import polars as pl

# Column-grain provision: which optional canonical columns the client actually
# supplied. Recorded at ingest, because complete_canonical_shape() makes the
# column exist-and-be-NULL either way afterwards.
import onboarding as _onb

CONTRACT_EXCEPTIONS_PATH = "data/gold/contract_exceptions.parquet"

# Column order is the contract between this writer and stg_data_quality.
GOLD_SCHEMA = {
    "employee_id": pl.Utf8,
    "employee_name": pl.Utf8,
    "issue_type": pl.Utf8,
    "description": pl.Utf8,
    "severity": pl.Utf8,
    "recommended_action": pl.Utf8,
    "source": pl.Utf8,
    "source_table": pl.Utf8,
    "source_row": pl.Int64,
    "source_column": pl.Utf8,
    "rule": pl.Utf8,
}


# GRAIN NOTE, for whoever generalises this into a loop over contracted tables.
#
# Every check below is written against a NAMED table - employees, payroll,
# attendance, hr_requests - and each assumes an employee_id. That is why adding
# `locations`, the first contracted table with no employee column, needed no
# change here: a reference dimension is simply never walked.
#
# The moment this becomes `for table in contracted_tables()`, that stops being
# true and `locations` (and any future reference dimension) starts being fed to
# checks that assume a per-employee grain. The guard machinery in
# scripts/onboarding.py IS grain-agnostic and was verified as such; this module
# is not, and only escapes the question by not asking it.
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
            "recommended_action": action,
            # Provenance (cycle 1b-ii). Additive: stg_data_quality is SELECT *
            # and both downstream models select their columns explicitly, so
            # no mart output changes. Contract violations arrive with these
            # populated; the checks below are the "validation" source.
            "source": "validation",
            "source_table": None,
            "source_row": None,
            "source_column": None,
            "rule": None,
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

        # Check Active employees checks (manager, location, salary)
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

        # Missing Location.
        #
        # Was "Missing Project" until 2026-08. The column was renamed, not
        # repurposed: it always held the physical site. An employee with no
        # site cannot be placed anywhere, which is the same defect under its
        # right name. A site that IS supplied but is absent from the client's
        # locations file is a DIFFERENT problem and is reported separately by
        # mart_unmatched_locations - one is a hole in the employee record, the
        # other is a hole in the reference file.
        missing_loc = active_emps.filter(
            pl.col("location").is_null() | (pl.col("location") == ""))
        for r in missing_loc.iter_rows(named=True):
            add_issue(
                r["employee_id"],
                r["employee_name"],
                "Missing Location",
                "Active employee has no location assigned.",
                "Warning",
                "Assign a location in the master profile"
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

        # Missing Cost Center.
        #
        # Scoped to clients who PROVIDE the column. A missing VALUE in a
        # provided column is a data-quality exception - this record is
        # incomplete and someone should fix it. An ABSENT COLUMN is a coverage
        # fact: the client does not track cost centres, and no amount of HR
        # work will change it. Firing per employee for the second case would
        # put one row per person on the Data Quality page and bury every real
        # finding.
        #
        # The check cannot ask the data, because complete_canonical_shape() has
        # already added the column as typed NULL - by design, so nothing
        # downstream crashes. onboarding.provides_column() is where the
        # distinction was recorded, at ingest, while it was still knowable.
        if _onb.provides_column("employees", "cost_center"):
            missing_cc = df_emp.filter(
                pl.col("cost_center").is_null() | (pl.col("cost_center") == ""))
            for r in missing_cc.iter_rows(named=True):
                add_issue(
                    r["employee_id"],
                    r["employee_name"],
                    "Missing Cost Center",
                    "Employee has no cost center assigned.",
                    "Warning",
                    "Assign financial cost center code in master profile"
                )
        else:
            print("[coverage] employees: no cost_center column in the client's "
                  "file. Cost-centre checks skipped - an absent column is a "
                  "coverage fact, not one exception per employee.")

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
        df_gold = pl.DataFrame(issues, schema=GOLD_SCHEMA)
    else:
        # Create empty with proper schema
        df_gold = pl.DataFrame(schema=GOLD_SCHEMA)

    # Merge EXCEPTION-severity contract violations produced by ingest. The file
    # is written only on the real path and is unlinked at the start of every
    # ingest run, so in demo it is absent and this is a no-op.
    n_contract = 0
    if os.path.exists(CONTRACT_EXCEPTIONS_PATH):
        df_contract = pl.read_parquet(CONTRACT_EXCEPTIONS_PATH)
        n_contract = df_contract.height
        if n_contract:
            df_gold = pl.concat([df_gold, df_contract.select(list(GOLD_SCHEMA))],
                                how="vertical")

    df_gold.write_parquet("data/gold/data_quality_report.parquet")
    total = len(issues) + n_contract
    suffix = f" (+{n_contract} from contract validation)" if n_contract else ""
    print(f"Validation complete. Generated {total} issues{suffix} in data/gold/data_quality_report.parquet")

if __name__ == "__main__":
    validate()
