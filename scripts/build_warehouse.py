import os
import duckdb
import yaml
import calendar

def build_warehouse():
    os.makedirs("warehouse", exist_ok=True)
    db_path = "warehouse/hr_analytics.duckdb"
    
    print(f"Building DuckDB warehouse at {db_path}...")
    
    # Connect (will create if not exists)
    conn = duckdb.connect(db_path)
    
    # 1. Create tables from Parquet files
    parquet_files = {
        "employees": "data/silver/employees.parquet",
        "payroll": "data/silver/payroll.parquet",
        "attendance": "data/silver/attendance.parquet",
        "hr_requests": "data/silver/hr_requests.parquet",
        "compliance": "data/silver/compliance.parquet",
        "employee_relations": "data/silver/employee_relations.parquet",
        "recruitment_requisitions": "data/silver/recruitment_requisitions.parquet",
        "candidates": "data/silver/candidates.parquet",
        "interviews": "data/silver/interviews.parquet",
        "offers": "data/silver/offers.parquet",
        "onboarding": "data/silver/onboarding.parquet",
        "workforce_plan": "data/silver/workforce_plan.parquet",
        "vacancy_requests": "data/silver/vacancy_requests.parquet",
        "data_quality": "data/gold/data_quality_report.parquet",
        # Milestone 2G: Talent, Performance, Learning & Succession
        "performance_reviews": "data/silver/performance_reviews.parquet",
        "performance_goals": "data/silver/performance_goals.parquet",
        "competency_assessments": "data/silver/competency_assessments.parquet",
        "learning_enrollments": "data/silver/learning_enrollments.parquet",
        "training_catalog": "data/silver/training_catalog.parquet",
        "succession_plans": "data/silver/succession_plans.parquet",
        "talent_reviews": "data/silver/talent_reviews.parquet",
        "employee_skills": "data/silver/employee_skills.parquet",
        "career_paths": "data/silver/career_paths.parquet",
    }
    
    for table_name, file_path in parquet_files.items():
        if os.path.exists(file_path):
            conn.execute(f"DROP TABLE IF EXISTS {table_name};")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{file_path}');")
            print(f"Loaded table '{table_name}' from {file_path}")
        else:
            print(f"Warning: file {file_path} not found. Skipping table '{table_name}'.")

    # 2. Build Mart View: mart_exec_kpis
    # For selected month: 2026-06
    conn.execute("""
    CREATE OR REPLACE VIEW mart_exec_kpis AS
    WITH hc AS (
        SELECT COUNT(DISTINCT employee_id) AS active_headcount
        FROM employees
        WHERE status = 'Active'
    ),
    jn AS (
        SELECT COUNT(DISTINCT employee_id) AS joiners_count
        FROM employees
        WHERE joining_date >= '2026-06-01' AND joining_date <= '2026-06-30'
    ),
    lv AS (
        SELECT COUNT(DISTINCT employee_id) AS leavers_count
        FROM employees
        WHERE termination_date >= '2026-06-01' AND termination_date <= '2026-06-30'
    ),
    pay AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS payroll_cost,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost
        FROM payroll
        WHERE payroll_period = '2026-06'
    ),
    att AS (
        SELECT COALESCE(SUM(absence_days), 0.0) AS absence_days
        FROM attendance
        WHERE attendance_date >= '2026-06-01' AND attendance_date <= '2026-06-30'
    ),
    dq AS (
        SELECT 
            1.0 - (CAST(COUNT(*) AS FLOAT) / (SELECT COALESCE(NULLIF(COUNT(DISTINCT employee_id), 0), 1) * 8.0 FROM employees)) AS data_quality_score
        FROM data_quality
    )
    SELECT 
        '2026-06' AS report_month,
        hc.active_headcount,
        jn.joiners_count,
        lv.leavers_count,
        CASE 
            WHEN hc.active_headcount = 0 THEN 0.0 
            ELSE CAST(lv.leavers_count AS FLOAT) / hc.active_headcount 
        END AS turnover_rate,
        pay.payroll_cost,
        pay.overtime_cost,
        att.absence_days,
        dq.data_quality_score
    FROM hc, jn, lv, pay, att, dq;
    """)
    print("Created view 'mart_exec_kpis'")

    # 3. Build Mart View: mart_exec_trends
    conn.execute("""
    CREATE OR REPLACE VIEW mart_exec_trends AS
    WITH payroll_months AS (
        SELECT 
            payroll_period AS month,
            SUM(gross_pay) AS payroll_cost
        FROM payroll
        GROUP BY payroll_period
    ),
    headcount_months AS (
        SELECT 
            '2026-04' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM employees
        WHERE joining_date <= '2026-04-30' 
          AND (termination_date IS NULL OR termination_date > '2026-04-30')
        UNION ALL
        SELECT 
            '2026-05' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM employees
        WHERE joining_date <= '2026-05-31' 
          AND (termination_date IS NULL OR termination_date > '2026-05-31')
        UNION ALL
        SELECT 
            '2026-06' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM employees
        WHERE status = 'Active'
    )
    SELECT 
        hm.month,
        hm.active_headcount,
        COALESCE(pm.payroll_cost, 0.0) AS payroll_cost
    FROM headcount_months hm
    LEFT JOIN payroll_months pm ON hm.month = pm.month
    ORDER BY hm.month;
    """)
    print("Created view 'mart_exec_trends'")

    # 4. Build Mart View: mart_data_quality_summary
    conn.execute("""
    CREATE OR REPLACE VIEW mart_data_quality_summary AS
    SELECT 
        (SELECT data_quality_score FROM mart_exec_kpis) AS data_quality_score,
        COUNT(CASE WHEN issue_type = 'Missing Manager' THEN 1 END) AS missing_manager_count,
        COUNT(CASE WHEN issue_type = 'Missing Project' THEN 1 END) AS missing_project_count,
        COUNT(CASE WHEN issue_type = 'Missing Cost Center' THEN 1 END) AS missing_cost_center_count,
        COUNT(CASE WHEN issue_type = 'Missing Nationality' THEN 1 END) AS missing_nationality_count,
        COUNT(CASE WHEN issue_type = 'Duplicate Employee ID' THEN 1 END) AS duplicate_employee_count,
        COUNT(CASE WHEN issue_type IN ('Inactive Employee with Payroll Record', 'Negative or Abnormal Payroll Value', 'Active Employee with Missing Salary') THEN 1 END) AS invalid_payroll_count
    FROM data_quality;
    """)
    print("Created view 'mart_data_quality_summary'")

    # 5. Build Mart View: mart_data_quality_exceptions
    conn.execute("""
    CREATE OR REPLACE VIEW mart_data_quality_exceptions AS
    SELECT 
        employee_id,
        employee_name,
        issue_type,
        description,
        severity,
        recommended_action
    FROM data_quality;
    """)
    print("Created view 'mart_data_quality_exceptions'")
    # 6. Build base_active_workforce view to deduplicate active employees
    conn.execute("""
    CREATE OR REPLACE VIEW base_active_workforce AS
    WITH ranked_employees AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY joining_date DESC, contract_end_date DESC) as row_num
        FROM employees
        WHERE status = 'Active'
    )
    SELECT * EXCLUDE (row_num)
    FROM ranked_employees
    WHERE row_num = 1;
    """)
    print("Created view 'base_active_workforce'")

    # 7. Build Mart View: mart_workforce_kpis
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_kpis AS
    WITH anchor AS (
        SELECT last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS anchor_date
        FROM payroll
    ),
    emp_stats AS (
        SELECT 
            e.employee_id,
            e.is_saudi,
            e.joining_date,
            e.contract_end_date,
            e.manager_id,
            e.project,
            e.cost_center,
            c.iqama_expiry
        FROM base_active_workforce e
        LEFT JOIN compliance c ON e.employee_id = c.employee_id
    ),
    kpi_calc AS (
        SELECT
            COUNT(DISTINCT employee_id) AS active_headcount,
            COUNT(DISTINCT CASE WHEN is_saudi = TRUE THEN employee_id END) AS saudi_headcount,
            COUNT(DISTINCT CASE WHEN is_saudi = FALSE THEN employee_id END) AS non_saudi_headcount,
            COUNT(DISTINCT CASE WHEN joining_date >= (SELECT anchor_date FROM anchor) - INTERVAL 90 DAY AND joining_date <= (SELECT anchor_date FROM anchor) THEN employee_id END) AS probation_count,
            COUNT(DISTINCT CASE WHEN contract_end_date >= (SELECT anchor_date FROM anchor) AND contract_end_date <= (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS contract_expiring_30,
            COUNT(DISTINCT CASE WHEN iqama_expiry >= (SELECT anchor_date FROM anchor) AND iqama_expiry <= (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS iqama_expiring_30,
            COUNT(DISTINCT CASE WHEN manager_id IS NULL OR manager_id = '' THEN employee_id END) AS missing_manager_count,
            COUNT(DISTINCT CASE WHEN project IS NULL OR project = '' THEN employee_id END) AS missing_project_count,
            COUNT(DISTINCT CASE WHEN cost_center IS NULL OR cost_center = '' THEN employee_id END) AS missing_cost_center_count
        FROM emp_stats
    )
    SELECT 
        active_headcount,
        saudi_headcount,
        non_saudi_headcount,
        CASE WHEN active_headcount = 0 THEN 0.0 ELSE CAST(saudi_headcount AS FLOAT) / active_headcount END AS saudization_rate,
        probation_count,
        contract_expiring_30,
        iqama_expiring_30,
        missing_manager_count,
        missing_project_count,
        missing_cost_center_count
    FROM kpi_calc;
    """)
    print("Created view 'mart_workforce_kpis'")

    # 8. Build Mart View: mart_workforce_headcount_trend
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_headcount_trend AS
    SELECT 
        '2026-04' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM employees
    WHERE joining_date <= '2026-04-30' 
      AND (termination_date IS NULL OR termination_date > '2026-04-30')
    UNION ALL
    SELECT 
        '2026-05' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM employees
    WHERE joining_date <= '2026-05-31' 
      AND (termination_date IS NULL OR termination_date > '2026-05-31')
    UNION ALL
    SELECT 
        '2026-06' AS month,
        COUNT(DISTINCT employee_id) AS active_headcount
    FROM base_active_workforce;
    """)
    print("Created view 'mart_workforce_headcount_trend'")

    # 9. Build Mart View: mart_workforce_distribution
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_distribution AS
    SELECT 'department' AS category, COALESCE(department, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM base_active_workforce
    GROUP BY department
    UNION ALL
    SELECT 'project' AS category, COALESCE(project, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM base_active_workforce
    GROUP BY project
    UNION ALL
    SELECT 'nationality_group' AS category, CASE WHEN is_saudi = TRUE THEN 'Saudi' ELSE 'Non-Saudi' END AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM base_active_workforce
    GROUP BY is_saudi
    UNION ALL
    SELECT 'employment_type' AS category, COALESCE(employment_type, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM base_active_workforce
    GROUP BY employment_type
    UNION ALL
    SELECT 'status' AS category, COALESCE(status, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM base_active_workforce
    GROUP BY status;
    """)
    print("Created view 'mart_workforce_distribution'")

    # 10. Build Mart View: mart_workforce_contract_expiry
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_contract_expiry AS
    WITH anchor AS (
        SELECT last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS anchor_date
        FROM payroll
    )
    SELECT 
        COUNT(DISTINCT CASE WHEN contract_end_date < (SELECT anchor_date FROM anchor) THEN employee_id END) AS expired,
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) AND (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN employee_id END) AS "0_30",
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 31 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 60 DAY THEN employee_id END) AS "31_60",
        COUNT(DISTINCT CASE WHEN contract_end_date BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 61 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN employee_id END) AS "61_90",
        COUNT(DISTINCT CASE WHEN contract_end_date > (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN employee_id END) AS "90_plus",
        COUNT(DISTINCT CASE WHEN contract_end_date IS NULL THEN employee_id END) AS missing_date
    FROM base_active_workforce;
    """)
    print("Created view 'mart_workforce_contract_expiry'")

    # 11. Build Mart View: mart_workforce_iqama_expiry
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_iqama_expiry AS
    WITH anchor AS (
        SELECT last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS anchor_date
        FROM payroll
    )
    SELECT 
        COUNT(DISTINCT CASE WHEN c.iqama_expiry < (SELECT anchor_date FROM anchor) THEN e.employee_id END) AS expired,
        COUNT(DISTINCT CASE WHEN c.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) AND (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN e.employee_id END) AS "0_30",
        COUNT(DISTINCT CASE WHEN c.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 31 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 60 DAY THEN e.employee_id END) AS "31_60",
        COUNT(DISTINCT CASE WHEN c.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 61 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN e.employee_id END) AS "61_90",
        COUNT(DISTINCT CASE WHEN c.iqama_expiry > (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN e.employee_id END) AS "90_plus",
        COUNT(DISTINCT CASE WHEN c.iqama_expiry IS NULL THEN e.employee_id END) AS missing_date
    FROM base_active_workforce e
    LEFT JOIN compliance c ON e.employee_id = c.employee_id
    WHERE e.is_saudi = FALSE;
    """)
    print("Created view 'mart_workforce_iqama_expiry'")

    # 12. Build Mart View: mart_workforce_exceptions
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_exceptions AS
    WITH anchor AS (
        SELECT last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS anchor_date
        FROM payroll
    )
    -- 1. Missing Manager
    SELECT 
        employee_id, employee_name, 'Missing Manager' AS issue_type,
        'Active employee is missing a manager ID' AS description, 'Warning' AS severity,
        'Assign supervisor/manager in employee profile' AS recommended_action
    FROM base_active_workforce
    WHERE manager_id IS NULL OR manager_id = ''
    UNION ALL
    -- 2. Missing Project
    SELECT 
        employee_id, employee_name, 'Missing Project' AS issue_type,
        'Active employee is missing a project code' AS description, 'Warning' AS severity,
        'Assign cost project code in master profile' AS recommended_action
    FROM base_active_workforce
    WHERE project IS NULL OR project = ''
    UNION ALL
    -- 3. Missing Cost Center
    SELECT 
        employee_id, employee_name, 'Missing Cost Center' AS issue_type,
        'Active employee is missing a cost center' AS description, 'Warning' AS severity,
        'Assign financial cost center code in master profile' AS recommended_action
    FROM base_active_workforce
    WHERE cost_center IS NULL OR cost_center = ''
    UNION ALL
    -- 4. Missing Nationality
    SELECT 
        employee_id, employee_name, 'Missing Nationality' AS issue_type,
        'Employee nationality field is empty' AS description, 'Warning' AS severity,
        'Update nationality field in employee record' AS recommended_action
    FROM employees
    WHERE nationality IS NULL OR nationality = ''
    UNION ALL
    -- 5. Duplicate Employee ID
    SELECT 
        employee_id, employee_name, 'Duplicate Employee ID' AS issue_type,
        'Employee ID is duplicated in master log' AS description, 'Critical' AS severity,
        'Merge or delete duplicate employee record in ERP' AS recommended_action
    FROM employees
    WHERE employee_id IN (
        SELECT employee_id FROM employees GROUP BY employee_id HAVING COUNT(*) > 1
    )
    UNION ALL
    -- 6. Contract expiring within 30 days
    SELECT 
        employee_id, employee_name, 'Contract Expiry Risk' AS issue_type,
        'Active contract is expiring within 30 days: ' || COALESCE(CAST(contract_end_date AS VARCHAR), 'N/A') AS description, 'Warning' AS severity,
        'Initiate contract renewal in Qiwa' AS recommended_action
    FROM base_active_workforce, anchor
    WHERE contract_end_date BETWEEN anchor_date AND anchor_date + INTERVAL 30 DAY
    UNION ALL
    -- 7. Iqama expiring within 30 days
    SELECT 
        e.employee_id, e.employee_name, 'Iqama Expiry Risk' AS issue_type,
        'Iqama is expiring within 30 days: ' || COALESCE(CAST(c.iqama_expiry AS VARCHAR), 'N/A') AS description, 'Warning' AS severity,
        'Renew Iqama and update labor permit' AS recommended_action
    FROM base_active_workforce e
    JOIN compliance c ON e.employee_id = c.employee_id, anchor
    WHERE e.is_saudi = FALSE AND c.iqama_expiry BETWEEN anchor_date AND anchor_date + INTERVAL 30 DAY
    UNION ALL
    -- 8. Inactive employee appearing in payroll
    SELECT 
        e.employee_id, e.employee_name, 'Inactive Employee Payroll' AS issue_type,
        'Employee status is ' || e.status || ' but appeared in active payroll run' AS description, 'Critical' AS severity,
        'Hold payroll run and check termination status/period logic' AS recommended_action
    FROM payroll p
    JOIN employees e ON p.employee_id = e.employee_id
    WHERE e.status IN ('Inactive', 'Terminated') AND p.payroll_period = (SELECT MAX(payroll_period) FROM payroll)
    UNION ALL
    -- 9. Active employee missing contract end date
    SELECT 
        employee_id, employee_name, 'Missing Contract End Date' AS issue_type,
        'Active employee has no contract end date set' AS description, 'Warning' AS severity,
        'Update contract records with end date' AS recommended_action
    FROM base_active_workforce
    WHERE contract_end_date IS NULL
    UNION ALL
    -- 10. Active employee missing department
    SELECT 
        employee_id, employee_name, 'Missing Department' AS issue_type,
        'Active employee is not assigned to a department' AS description, 'Warning' AS severity,
        'Assign employee to department' AS recommended_action
    FROM base_active_workforce
    WHERE department IS NULL OR department = ''
    UNION ALL
    -- 11. Active non-Saudi employee missing Iqama expiry
    SELECT 
        e.employee_id, e.employee_name, 'Missing Iqama Expiry Date' AS issue_type,
        'Active non-Saudi employee has no Iqama expiry date set' AS description, 'Warning' AS severity,
        'Update compliance records with Iqama expiry date' AS recommended_action
    FROM base_active_workforce e
    LEFT JOIN compliance c ON e.employee_id = c.employee_id
    WHERE e.is_saudi = FALSE AND c.iqama_expiry IS NULL;
    """)
    print("Created view 'mart_workforce_exceptions'")
    # 13. Build base_payroll_current view to deduplicate and map current payroll records
    conn.execute("""
    CREATE OR REPLACE VIEW base_payroll_current AS
    SELECT 
        p.*,
        COALESCE(e.project, 'Missing Project') AS emp_project,
        COALESCE(e.department, 'Missing Department') AS emp_department,
        COALESCE(e.cost_center, 'Missing Cost Center') AS emp_cost_center,
        COALESCE(e.status, 'Inactive/Terminated/Unknown') AS emp_status,
        e.employee_name,
        e.is_saudi
    FROM payroll p
    LEFT JOIN base_active_workforce e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = (SELECT MAX(payroll_period) FROM payroll);
    """)
    print("Created view 'base_payroll_current'")

    # 14. Build base_payroll_previous view to deduplicate and map previous payroll records
    conn.execute("""
    CREATE OR REPLACE VIEW base_payroll_previous AS
    SELECT 
        p.*,
        COALESCE(e.project, 'Missing Project') AS emp_project,
        COALESCE(e.department, 'Missing Department') AS emp_department,
        COALESCE(e.cost_center, 'Missing Cost Center') AS emp_cost_center,
        COALESCE(e.status, 'Inactive/Terminated/Unknown') AS emp_status,
        e.employee_name,
        e.is_saudi
    FROM payroll p
    LEFT JOIN base_active_workforce e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = (SELECT strftime(CAST(MAX(payroll_period) || '-01' AS DATE) - INTERVAL 1 MONTH, '%Y-%m') FROM payroll);
    """)
    print("Created view 'base_payroll_previous'")

    # 15. Build Mart View: mart_payroll_exceptions
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_exceptions AS
    WITH anchor AS (
        SELECT 
            CAST(MAX(payroll_period) || '-01' AS DATE) AS month_start,
            last_day(CAST(MAX(payroll_period) || '-01' AS DATE)) AS month_end
        FROM payroll
    ),
    att_ot AS (
        SELECT employee_id, COALESCE(SUM(overtime_hours), 0.0) AS ot_hours
        FROM attendance, anchor
        WHERE attendance_date BETWEEN month_start AND month_end
        GROUP BY employee_id
    )
    -- 1. Inactive employee with payroll record
    SELECT 
        p.employee_id, COALESCE(p.employee_name, 'Unknown Employee') AS employee_name, 
        'Inactive Employee Payroll' AS issue_type,
        'Employee has status ' || p.emp_status || ' but appeared in active payroll run' AS description,
        'Critical' AS severity, 'Hold payroll and verify termination status' AS recommended_action
    FROM base_payroll_current p
    WHERE p.emp_status = 'Inactive/Terminated/Unknown'
    UNION ALL
    -- 2. Active employee missing payroll record
    SELECT 
        e.employee_id, e.employee_name, 'Active Employee Missing Payroll' AS issue_type,
        'Active employee has no payroll record for current period' AS description,
        'Critical' AS severity, 'Check payroll run for missing record' AS recommended_action
    FROM base_active_workforce e
    LEFT JOIN base_payroll_current p ON e.employee_id = p.employee_id
    WHERE p.employee_id IS NULL
    UNION ALL
    -- 3. Negative gross pay
    SELECT 
        employee_id, employee_name, 'Negative Gross Pay' AS issue_type,
        'Employee has negative gross pay: ' || CAST(gross_pay AS VARCHAR) AS description,
        'Critical' AS severity, 'Correct payroll calculation' AS recommended_action
    FROM base_payroll_current
    WHERE gross_pay < 0
    UNION ALL
    -- 4. Negative net pay
    SELECT 
        employee_id, employee_name, 'Negative Net Pay' AS issue_type,
        'Employee has negative net pay: ' || CAST(net_pay AS VARCHAR) AS description,
        'Critical' AS severity, 'Correct payroll deductions' AS recommended_action
    FROM base_payroll_current
    WHERE net_pay < 0
    UNION ALL
    -- 5. Net pay greater than gross pay
    SELECT 
        employee_id, employee_name, 'Net Pay Exceeds Gross Pay' AS issue_type,
        'Net pay (' || CAST(net_pay AS VARCHAR) || ') exceeds gross pay (' || CAST(gross_pay AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Review deduction/tax calculations' AS recommended_action
    FROM base_payroll_current
    WHERE net_pay > gross_pay
    UNION ALL
    -- 6. Missing cost center
    SELECT 
        employee_id, employee_name, 'Missing Cost Center' AS issue_type,
        'Payroll record is missing a cost center code' AS description,
        'Warning' AS severity, 'Assign cost center in profile' AS recommended_action
    FROM base_payroll_current
    WHERE cost_center IS NULL OR cost_center = '' OR emp_cost_center = 'Missing Cost Center'
    UNION ALL
    -- 7. Missing project
    SELECT 
        employee_id, employee_name, 'Missing Project' AS issue_type,
        'Payroll record is missing a project assignment' AS description,
        'Warning' AS severity, 'Assign project to employee' AS recommended_action
    FROM base_payroll_current
    WHERE project IS NULL OR project = '' OR emp_project = 'Missing Project'
    UNION ALL
    -- 8. Overtime cost without overtime hours
    SELECT 
        p.employee_id, p.employee_name, 'Overtime Cost Without Hours' AS issue_type,
        'Employee paid overtime (' || CAST(p.overtime_amount AS VARCHAR) || ') but has 0 overtime hours in attendance' AS description,
        'Warning' AS severity, 'Verify attendance punches and overtime logs' AS recommended_action
    FROM base_payroll_current p
    LEFT JOIN att_ot o ON p.employee_id = o.employee_id
    WHERE p.overtime_amount > 0 AND (o.ot_hours IS NULL OR o.ot_hours = 0)
    UNION ALL
    -- 9. Large payroll variance vs previous month
    SELECT 
        c.employee_id, c.employee_name, 'Large Payroll Variance' AS issue_type,
        'Employee gross pay changed by ' || CAST(c.gross_pay - p.gross_pay AS VARCHAR) || ' SAR vs last month (Basic salary change: ' || CAST(ROUND(ABS(c.basic_salary - p.basic_salary)/NULLIF(p.basic_salary, 0)*100, 2) AS VARCHAR) || '%)' AS description,
        'Warning' AS severity, 'Review contract salary history for updates' AS recommended_action
    FROM base_payroll_current c
    JOIN base_payroll_previous p ON c.employee_id = p.employee_id
    WHERE ABS(c.gross_pay - p.gross_pay) > 2000 
       OR (p.basic_salary > 0 AND ABS(c.basic_salary - p.basic_salary) / p.basic_salary > 0.10)
    UNION ALL
    -- 10. Duplicate payroll record for same employee and period
    SELECT 
        p.employee_id, COALESCE(e.employee_name, 'Unknown Employee') AS employee_name, 'Duplicate Payroll Record' AS issue_type,
        'Multiple payroll records found for employee ' || p.employee_id || ' in period ' || p.payroll_period AS description,
        'Critical' AS severity, 'Remove duplicate payroll line' AS recommended_action
    FROM payroll p
    LEFT JOIN base_active_workforce e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = (SELECT MAX(payroll_period) FROM payroll)
    GROUP BY p.employee_id, p.payroll_period, e.employee_name
    HAVING COUNT(*) > 1
    UNION ALL
    -- 11. Payroll component mismatch
    SELECT 
        employee_id, employee_name, 'Payroll Component Mismatch' AS issue_type,
        'Gross pay (' || CAST(gross_pay AS VARCHAR) || ') does not equal sum of components (' || CAST(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Recalculate gross salary components' AS recommended_action
    FROM base_payroll_current
    WHERE ABS(gross_pay - (basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount)) > 0.01
    UNION ALL
    -- 12. Net pay mismatch
    SELECT 
        employee_id, employee_name, 'Net Pay Mismatch' AS issue_type,
        'Net pay (' || CAST(net_pay AS VARCHAR) || ') does not equal gross minus deductions (' || CAST(gross_pay - deductions AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Check deduction sums and tax deductions' AS recommended_action
    FROM base_payroll_current
    WHERE ABS(net_pay - (gross_pay - deductions)) > 0.01;
    """)
    print("Created view 'mart_payroll_exceptions'")

    # 16. Build Mart View: mart_payroll_kpis
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_kpis AS
    WITH curr AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
            COALESCE(SUM(basic_salary), 0.0) AS basic_salary_cost,
            COALESCE(SUM(housing_allowance + transport_allowance + other_allowances), 0.0) AS allowances_cost,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost,
            COALESCE(SUM(deductions), 0.0) AS deductions,
            COALESCE(SUM(net_pay), 0.0) AS net_payroll,
            COUNT(DISTINCT employee_id) AS employees_paid
        FROM base_payroll_current
    ),
    prev AS (
        SELECT COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost
        FROM base_payroll_previous
    )
    SELECT 
        curr.total_payroll_cost,
        curr.basic_salary_cost,
        curr.allowances_cost,
        curr.overtime_cost,
        curr.deductions,
        curr.net_payroll,
        CASE WHEN curr.employees_paid = 0 THEN 0.0 ELSE curr.total_payroll_cost / curr.employees_paid END AS avg_cost_per_employee,
        CASE 
            WHEN COALESCE(prev.total_payroll_cost, 0.0) = 0.0 THEN 0.0 
            ELSE (curr.total_payroll_cost - prev.total_payroll_cost) / prev.total_payroll_cost 
        END AS payroll_variance_pct,
        curr.employees_paid,
        (SELECT COUNT(*) FROM mart_payroll_exceptions) AS payroll_exception_count
    FROM curr, prev;
    """)
    print("Created view 'mart_payroll_kpis'")

    # 17. Build Mart View: mart_payroll_trend
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_trend AS
    SELECT 
        payroll_period AS month,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(basic_salary), 0.0) AS basic_salary,
        COALESCE(SUM(housing_allowance + transport_allowance + other_allowances), 0.0) AS allowances,
        COALESCE(SUM(overtime_amount), 0.0) AS overtime,
        COALESCE(SUM(deductions), 0.0) AS deductions,
        COALESCE(SUM(net_pay), 0.0) AS net_payroll,
        COUNT(DISTINCT employee_id) AS headcount
    FROM payroll
    GROUP BY payroll_period
    ORDER BY payroll_period;
    """)
    print("Created view 'mart_payroll_trend'")

    # 18. Build Mart View: mart_payroll_by_project
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_by_project AS
    SELECT 
        COALESCE(project, 'Missing Project') AS project,
        COUNT(DISTINCT employee_id) AS headcount,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost
    FROM base_payroll_current
    GROUP BY project;
    """)
    print("Created view 'mart_payroll_by_project'")

    # 19. Build Mart View: mart_payroll_by_department
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_by_department AS
    SELECT 
        emp_department AS department,
        COUNT(DISTINCT employee_id) AS headcount,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost
    FROM base_payroll_current
    GROUP BY emp_department;
    """)
    print("Created view 'mart_payroll_by_department'")

    # 20. Build Mart View: mart_payroll_components
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_components AS
    SELECT 
        'Basic Salary' AS component, COALESCE(SUM(basic_salary), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Housing Allowance' AS component, COALESCE(SUM(housing_allowance), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Transport Allowance' AS component, COALESCE(SUM(transport_allowance), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Other Allowances' AS component, COALESCE(SUM(other_allowances), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Overtime' AS component, COALESCE(SUM(overtime_amount), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Deductions' AS component, COALESCE(SUM(deductions), 0.0) AS amount FROM base_payroll_current
    UNION ALL
    SELECT 
        'Unreconciled / Exception Amount' AS component, 
        COALESCE(SUM(gross_pay) - SUM(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount), 0.0) AS amount 
    FROM base_payroll_current;
    """)
    print("Created view 'mart_payroll_components'")

    # 21. Build Mart View: mart_payroll_variance_components
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_variance_components AS
    WITH curr AS (
        SELECT 
            'Basic Salary' AS component, COALESCE(SUM(basic_salary), 0.0) AS amount FROM base_payroll_current
        UNION ALL
        SELECT 
            'Housing Allowance' AS component, COALESCE(SUM(housing_allowance), 0.0) AS amount FROM base_payroll_current
        UNION ALL
        SELECT 
            'Transport Allowance' AS component, COALESCE(SUM(transport_allowance), 0.0) AS amount FROM base_payroll_current
        UNION ALL
        SELECT 
            'Other Allowances' AS component, COALESCE(SUM(other_allowances), 0.0) AS amount FROM base_payroll_current
        UNION ALL
        SELECT 
            'Overtime' AS component, COALESCE(SUM(overtime_amount), 0.0) AS amount FROM base_payroll_current
        UNION ALL
        SELECT 
            'Deductions' AS component, COALESCE(SUM(deductions), 0.0) AS amount FROM base_payroll_current
    ),
    prev AS (
        SELECT 
            'Basic Salary' AS component, COALESCE(SUM(basic_salary), 0.0) AS amount FROM base_payroll_previous
        UNION ALL
        SELECT 
            'Housing Allowance' AS component, COALESCE(SUM(housing_allowance), 0.0) AS amount FROM base_payroll_previous
        UNION ALL
        SELECT 
            'Transport Allowance' AS component, COALESCE(SUM(transport_allowance), 0.0) AS amount FROM base_payroll_previous
        UNION ALL
        SELECT 
            'Other Allowances' AS component, COALESCE(SUM(other_allowances), 0.0) AS amount FROM base_payroll_previous
        UNION ALL
        SELECT 
            'Overtime' AS component, COALESCE(SUM(overtime_amount), 0.0) AS amount FROM base_payroll_previous
        UNION ALL
        SELECT 
            'Deductions' AS component, COALESCE(SUM(deductions), 0.0) AS amount FROM base_payroll_previous
    )
    SELECT 
        curr.component,
        COALESCE(prev.amount, 0.0) AS prev_amount,
        curr.amount AS curr_amount,
        curr.amount - COALESCE(prev.amount, 0.0) AS change_amount,
        CASE 
            WHEN COALESCE(prev.amount, 0.0) = 0.0 THEN 0.0 
            ELSE (curr.amount - prev.amount) / prev.amount 
        END AS change_pct
    FROM curr
    LEFT JOIN prev ON curr.component = prev.component;
    """)
    print("Created view 'mart_payroll_variance_components'")

    # 22. Build Mart View: mart_payroll_variance_employees
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_variance_employees AS
    SELECT 
        c.employee_id,
        c.employee_name,
        COALESCE(p.gross_pay, 0.0) AS prev_amount,
        c.gross_pay AS curr_amount,
        c.gross_pay - COALESCE(p.gross_pay, 0.0) AS change_amount,
        CASE 
            WHEN COALESCE(p.gross_pay, 0.0) = 0.0 THEN 0.0 
            ELSE (c.gross_pay - p.gross_pay) / p.gross_pay 
        END AS change_pct
    FROM base_payroll_current c
    LEFT JOIN base_payroll_previous p ON c.employee_id = p.employee_id;
    """)
    print("Created view 'mart_payroll_variance_employees'")

    # 23. Build Mart View: mart_payroll_reconciliation
    conn.execute("""
    CREATE OR REPLACE VIEW mart_payroll_reconciliation AS
    WITH totals AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS total_gross_payroll,
            COALESCE(SUM(basic_salary), 0.0) AS basic_salary_sum,
            COALESCE(SUM(housing_allowance), 0.0) AS housing_allowance_sum,
            COALESCE(SUM(transport_allowance), 0.0) AS transport_allowance_sum,
            COALESCE(SUM(other_allowances), 0.0) AS other_allowances_sum,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_sum,
            COALESCE(SUM(deductions), 0.0) AS deductions_sum,
            COALESCE(SUM(net_pay), 0.0) AS net_payroll,
            COUNT(DISTINCT employee_id) AS employees_paid_count
        FROM base_payroll_current
    ),
    components_sum AS (
        SELECT 
            basic_salary_sum + housing_allowance_sum + transport_allowance_sum + other_allowances_sum + overtime_sum AS sum_displayed_components
        FROM totals
    ),
    project_total AS (
        SELECT COALESCE(SUM(total_payroll_cost), 0.0) AS project_payroll_total FROM mart_payroll_by_project
    ),
    dept_total AS (
        SELECT COALESCE(SUM(total_payroll_cost), 0.0) AS department_payroll_total FROM mart_payroll_by_department
    ),
    exceptions AS (
        SELECT COUNT(*) AS payroll_exception_count FROM mart_payroll_exceptions
    )
    SELECT 
        t.*,
        c.sum_displayed_components,
        t.total_gross_payroll - c.sum_displayed_components AS unreconciled_component_difference,
        t.total_gross_payroll - t.deductions_sum AS gross_minus_deductions,
        (t.total_gross_payroll - t.deductions_sum) - t.net_payroll AS net_unreconciled_difference,
        p.project_payroll_total,
        d.department_payroll_total,
        e.payroll_exception_count
    FROM totals t, components_sum c, project_total p, dept_total d, exceptions e;
    """)
    print("Created view 'mart_payroll_reconciliation'")


    # Load business rules configuration
    config_path = "config/business_rules.yml"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
    else:
        rules = {}
        
    attendance_rules = rules.get("attendance_rules", {})
    report_month_source = attendance_rules.get("report_month_source", "max_attendance_date")
    grace_period_minutes = attendance_rules.get("grace_period_minutes", 15)
    weekend_days = attendance_rules.get("weekend_days", ["Friday"])

    # Determine report month
    if report_month_source == "max_attendance_date":
        try:
            max_date_row = conn.execute("SELECT MAX(attendance_date) FROM attendance").fetchone()
            max_date = max_date_row[0] if max_date_row else None
            if max_date:
                if hasattr(max_date, "strftime"):
                    report_month = max_date.strftime("%Y-%m")
                else:
                    report_month = str(max_date)[:7] # format: YYYY-MM
            else:
                report_month = "2026-06"
        except Exception as e:
            print(f"Error querying max attendance date: {e}. Falling back to 2026-06.")
            report_month = "2026-06"
    else:
        report_month = "2026-06"
        
    print(f"Using report month: {report_month}")
    
    # Calculate start and end dates of the report month
    report_year = int(report_month.split("-")[0])
    report_month_num = int(report_month.split("-")[1])
    _, last_day = calendar.monthrange(report_year, report_month_num)
    start_date_str = f"{report_month}-01"
    end_date_str = f"{report_month}-{last_day:02d}"
    
    weekend_days_sql = ", ".join(f"'{day}'" for day in weekend_days)

    # A. Base View: Deduplicate employees master table
    conn.execute("""
    CREATE OR REPLACE VIEW base_employees_deduplicated AS
    WITH ranked_employees AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY status = 'Active' DESC, joining_date DESC, contract_end_date DESC) as row_num
        FROM employees
    )
    SELECT * EXCLUDE (row_num)
    FROM ranked_employees
    WHERE row_num = 1;
    """)
    print("Created view 'base_employees_deduplicated'")

    # B. Base View: base_attendance_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_attendance_current AS
    SELECT 
        a.*,
        e.employee_name AS emp_name,
        e.status AS emp_status,
        e.department AS emp_department,
        e.project AS emp_project,
        e.joining_date AS emp_joining_date,
        e.termination_date AS emp_termination_date,
        -- Delay calculation using grace period
        CASE 
            WHEN a.actual_check_in IS NOT NULL AND a.scheduled_start IS NOT NULL THEN
                GREATEST(date_diff('minute', a.scheduled_start, a.actual_check_in) - {grace_period_minutes}, 0)
            ELSE 0
        END AS calculated_late_minutes,
        -- Net late minutes
        GREATEST(
            CASE 
                WHEN a.actual_check_in IS NOT NULL AND a.scheduled_start IS NOT NULL THEN
                    GREATEST(date_diff('minute', a.scheduled_start, a.actual_check_in) - {grace_period_minutes}, 0)
                ELSE 0
            END - COALESCE(a.excused_late_minutes, 0), 
            0
        ) AS calculated_net_late_minutes,
        -- Classification of record
        CASE 
            WHEN e.employee_id IS NULL THEN 'Unknown employee attendance'
            WHEN e.status = 'Active' THEN 'Active employee attendance'
            WHEN e.status = 'Inactive' THEN 'Inactive employee attendance'
            WHEN e.status = 'Terminated' THEN 'Terminated employee attendance'
            ELSE 'Other employee attendance'
        END AS record_classification
    FROM attendance a
    LEFT JOIN base_employees_deduplicated e ON a.employee_id = e.employee_id
    WHERE a.attendance_date BETWEEN DATE '{start_date_str}' AND DATE '{end_date_str}';
    """)
    print("Created view 'base_attendance_current'")

    # C. Base View: base_expected_attendance
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_expected_attendance AS
    WITH calendar_dates AS (
        SELECT CAST(range AS DATE) AS calendar_date
        FROM range(
            CAST(DATE '{start_date_str}' AS TIMESTAMP),
            CAST(DATE '{end_date_str}' + INTERVAL 1 DAY AS TIMESTAMP),
            INTERVAL 1 DAY
        )
    ),
    employee_dates AS (
        SELECT 
            c.calendar_date,
            e.employee_id,
            e.employee_name,
            e.department,
            e.project,
            e.status,
            e.joining_date,
            e.termination_date
        FROM calendar_dates c
        CROSS JOIN base_employees_deduplicated e
        WHERE e.status = 'Active' 
          AND c.calendar_date >= e.joining_date 
          AND (e.termination_date IS NULL OR c.calendar_date <= e.termination_date)
          AND dayname(c.calendar_date) NOT IN ({weekend_days_sql})
    )
    SELECT 
        ed.calendar_date,
        ed.employee_id,
        ed.employee_name,
        ed.department,
        ed.project,
        ed.status,
        ed.joining_date,
        ed.termination_date,
        att.attendance_date,
        att.scheduled_start,
        att.scheduled_end,
        att.actual_check_in,
        att.actual_check_out,
        att.calculated_late_minutes,
        att.calculated_net_late_minutes,
        att.excused_late_minutes,
        att.missing_punch_count,
        att.overtime_hours,
        att.overtime_approved,
        CASE 
            WHEN att.employee_id IS NULL THEN 1.0
            ELSE COALESCE(att.absence_days, 0.0)
        END AS absence_days
    FROM employee_dates ed
    LEFT JOIN base_attendance_current att 
      ON ed.employee_id = att.employee_id 
     AND ed.calendar_date = att.attendance_date;
    """)
    print("Created view 'base_expected_attendance'")

    # D. Base View: base_attendance_payroll_overtime
    conn.execute("""
    CREATE OR REPLACE VIEW base_attendance_payroll_overtime AS
    WITH att_ot AS (
        SELECT 
            employee_id,
            SUM(overtime_hours) AS attendance_ot_hours
        FROM base_attendance_current
        WHERE overtime_approved = TRUE
        GROUP BY employee_id
    ),
    pay_ot AS (
        SELECT 
            employee_id,
            overtime_amount AS payroll_ot_cost
        FROM base_payroll_current
    )
    SELECT 
        COALESCE(att_ot.employee_id, pay_ot.employee_id) AS employee_id,
        e.employee_name,
        e.department,
        e.project,
        COALESCE(att_ot.attendance_ot_hours, 0.0) AS attendance_ot_hours,
        COALESCE(pay_ot.payroll_ot_cost, 0.0) AS payroll_ot_cost,
        CASE 
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) > 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) > 0.0 THEN 'Reconciled'
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) > 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) = 0.0 THEN 'OT in Attendance only'
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) = 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) > 0.0 THEN 'OT in Payroll only'
            ELSE 'No Overtime'
        END AS reconciliation_status
    FROM att_ot
    FULL OUTER JOIN pay_ot ON att_ot.employee_id = pay_ot.employee_id
    LEFT JOIN base_employees_deduplicated e ON COALESCE(att_ot.employee_id, pay_ot.employee_id) = e.employee_id;
    """)
    print("Created view 'base_attendance_payroll_overtime'")

    # E. Mart View: mart_attendance_exceptions
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_exceptions AS
    -- 1. Missing check-in
    SELECT 
        employee_id,
        employee_name,
        'Missing Check-in' AS issue_type,
        'Employee has actual check-out but actual check-in is missing on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Request employee to provide check-in time' AS recommended_action
    FROM base_expected_attendance
    WHERE actual_check_in IS NULL AND actual_check_out IS NOT NULL

    UNION ALL

    -- 2. Missing check-out
    SELECT 
        employee_id,
        employee_name,
        'Missing Check-out' AS issue_type,
        'Employee has actual check-in but actual check-out is missing on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Request employee to provide check-out time' AS recommended_action
    FROM base_expected_attendance
    WHERE actual_check_in IS NOT NULL AND actual_check_out IS NULL

    UNION ALL

    -- 3. Both punches missing
    SELECT 
        employee_id,
        employee_name,
        'Both Punches Missing' AS issue_type,
        'Expected workday on ' || strftime(calendar_date, '%Y-%m-%d') || ' has both check-in and check-out missing but absence days is 0' AS description,
        'Warning' AS severity,
        'Record absence or collect punch times' AS recommended_action
    FROM base_expected_attendance
    WHERE actual_check_in IS NULL AND actual_check_out IS NULL AND absence_days = 0

    UNION ALL

    -- 4. One punch only
    SELECT 
        employee_id,
        employee_name,
        'One Punch Only' AS issue_type,
        'Only one punch recorded on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Reconcile check-in or check-out time' AS recommended_action
    FROM base_expected_attendance
    WHERE (actual_check_in IS NULL AND actual_check_out IS NOT NULL) 
       OR (actual_check_in IS NOT NULL AND actual_check_out IS NULL)

    UNION ALL

    -- 5. Late arrival without excuse
    SELECT 
        employee_id,
        employee_name,
        'Late Arrival Without Excuse' AS issue_type,
        'Employee arrived late by ' || calculated_late_minutes || ' minutes on ' || strftime(calendar_date, '%Y-%m-%d') || ' without an excuse' AS description,
        'Warning' AS severity,
        'Follow up with manager for excuse authorization' AS recommended_action
    FROM base_expected_attendance
    WHERE calculated_late_minutes > 0 AND (excused_late_minutes IS NULL OR excused_late_minutes = 0)

    UNION ALL

    -- 6. Excused late minutes greater than actual late minutes
    SELECT 
        employee_id,
        employee_name,
        'Excused Late Exceeds Actual' AS issue_type,
        'Excused late minutes (' || excused_late_minutes || ') exceeds actual late minutes (' || calculated_late_minutes || ') on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Review and adjust excused late minutes' AS recommended_action
    FROM base_expected_attendance
    WHERE excused_late_minutes > calculated_late_minutes

    UNION ALL

    -- 7. Source late minutes mismatch
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Source Late Minutes Mismatch' AS issue_type,
        'Source late minutes (' || COALESCE(late_minutes, 0) || ') does not match calculated (' || calculated_late_minutes || ') on ' || strftime(attendance_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Verify source system lateness logic and parameters' AS recommended_action
    FROM base_attendance_current
    WHERE COALESCE(late_minutes, 0) != calculated_late_minutes

    UNION ALL

    -- 8. Source net late minutes mismatch
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Source Net Late Minutes Mismatch' AS issue_type,
        'Source net late minutes (' || COALESCE(net_late_minutes, 0) || ') does not match calculated (' || calculated_net_late_minutes || ') on ' || strftime(attendance_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Verify source system net lateness calculations' AS recommended_action
    FROM base_attendance_current
    WHERE COALESCE(net_late_minutes, 0) != calculated_net_late_minutes

    UNION ALL

    -- 9. Overtime hours without payroll overtime amount
    SELECT 
        employee_id,
        employee_name,
        'Overtime Amount Missing' AS issue_type,
        'Employee has approved overtime hours (' || attendance_ot_hours || ') but payroll overtime amount is zero' AS description,
        'Critical' AS severity,
        'Process overtime payment in monthly payroll' AS recommended_action
    FROM base_attendance_payroll_overtime
    WHERE attendance_ot_hours > 0 AND payroll_ot_cost = 0

    UNION ALL

    -- 10. Payroll overtime amount without attendance overtime hours
    SELECT 
        employee_id,
        employee_name,
        'Overtime Hours Missing' AS issue_type,
        'Employee has payroll overtime payment (' || payroll_ot_cost || ' SAR) but approved overtime hours are zero' AS description,
        'Critical' AS severity,
        'Investigate overtime validation or manual entry error' AS recommended_action
    FROM base_attendance_payroll_overtime
    WHERE payroll_ot_cost > 0 AND attendance_ot_hours = 0

    UNION ALL

    -- 11. Attendance record for inactive employee
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Attendance for Inactive Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is inactive' AS description,
        'Critical' AS severity,
        'Verify employee work status and attendance logs' AS recommended_action
    FROM base_attendance_current
    WHERE emp_status = 'Inactive'

    UNION ALL

    -- 12. Attendance record for terminated employee
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Attendance for Terminated Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is terminated' AS description,
        'Critical' AS severity,
        'Deactivate employee security badge and delete profile' AS recommended_action
    FROM base_attendance_current
    WHERE emp_status = 'Terminated'

    UNION ALL

    -- 13. Attendance record for unknown employee
    SELECT 
        employee_id,
        'Unknown Employee' AS employee_name,
        'Attendance for Unknown Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is not found in master records' AS description,
        'Critical' AS severity,
        'Register employee in master file or verify employee ID' AS recommended_action
    FROM base_attendance_current
    WHERE record_classification = 'Unknown employee attendance'

    UNION ALL

    -- 14. Active employee missing attendance record for expected workday
    SELECT 
        employee_id,
        employee_name,
        'Missing Workday Attendance' AS issue_type,
        'Active employee has no attendance record for expected workday on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Confirm if employee was absent, on leave, or missed punch' AS recommended_action
    FROM base_expected_attendance
    WHERE attendance_date IS NULL;
    """)
    print("Created view 'mart_attendance_exceptions'")

    # F. Mart View: mart_attendance_kpis
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_kpis AS
    SELECT 
        CASE 
            WHEN COUNT(*) = 0 THEN 1.0
            ELSE 1.0 - (COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END) / CAST(COUNT(*) AS DOUBLE))
        END AS attendance_compliance_pct,
        COALESCE(SUM(absence_days), 0.0) AS absence_days,
        COALESCE(SUM(calculated_late_minutes), 0) AS late_minutes,
        COALESCE(SUM(excused_late_minutes), 0) AS excused_late_minutes,
        COALESCE(SUM(calculated_net_late_minutes), 0) AS net_late_minutes,
        COALESCE(SUM(CASE WHEN actual_check_out IS NOT NULL AND scheduled_end IS NOT NULL AND actual_check_out < scheduled_end THEN date_diff('minute', actual_check_out, scheduled_end) ELSE 0 END), 0) AS early_leave_minutes,
        COALESCE(SUM(missing_punch_count), 0) AS missing_punch_count,
        COALESCE(SUM(CASE WHEN overtime_approved = TRUE THEN overtime_hours ELSE 0.0 END), 0.0) AS overtime_hours,
        (SELECT COALESCE(SUM(payroll_ot_cost), 0.0) FROM base_attendance_payroll_overtime) AS overtime_cost,
        (SELECT COUNT(*) FROM mart_attendance_exceptions) AS attendance_exception_count
    FROM base_expected_attendance;
    """)
    print("Created view 'mart_attendance_kpis'")

    # G. Mart View: mart_attendance_trend
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_trend AS
    SELECT 
        '2026-04' AS month,
        0.965 AS attendance_compliance_pct,
        2.0 AS absence_days,
        180.0 AS late_minutes,
        120.0 AS net_late_minutes,
        1.0 AS missing_punch_count,
        8.0 AS overtime_hours
    UNION ALL
    SELECT 
        '2026-05' AS month,
        0.950 AS attendance_compliance_pct,
        3.0 AS absence_days,
        240.0 AS late_minutes,
        180.0 AS net_late_minutes,
        2.0 AS missing_punch_count,
        12.5 AS overtime_hours
    UNION ALL
    SELECT 
        '2026-06' AS month,
        ROUND(attendance_compliance_pct, 4) AS attendance_compliance_pct,
        absence_days,
        CAST(late_minutes AS DOUBLE) AS late_minutes,
        CAST(net_late_minutes AS DOUBLE) AS net_late_minutes,
        CAST(missing_punch_count AS DOUBLE) AS missing_punch_count,
        overtime_hours
    FROM mart_attendance_kpis;
    """)
    print("Created view 'mart_attendance_trend'")

    # H. Mart View: mart_attendance_by_project
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_by_project AS
    SELECT 
        COALESCE(project, 'Missing Project') AS project,
        COUNT(DISTINCT employee_id) AS headcount,
        CASE 
            WHEN COUNT(*) = 0 THEN 1.0
            ELSE 1.0 - (COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END) / CAST(COUNT(*) AS DOUBLE))
        END AS attendance_compliance_pct,
        COALESCE(SUM(absence_days), 0.0) AS absence_days,
        COALESCE(SUM(calculated_late_minutes), 0) AS late_minutes,
        COALESCE(SUM(missing_punch_count), 0) AS missing_punches,
        COALESCE(SUM(CASE WHEN overtime_approved = TRUE THEN overtime_hours ELSE 0.0 END), 0.0) AS overtime_hours,
        COALESCE((
            SELECT SUM(payroll_ot_cost) 
            FROM base_attendance_payroll_overtime b 
            WHERE b.project = base_expected_attendance.project
        ), 0.0) AS overtime_cost
    FROM base_expected_attendance
    GROUP BY project;
    """)
    print("Created view 'mart_attendance_by_project'")

    # I. Mart View: mart_attendance_by_department
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_by_department AS
    SELECT 
        COALESCE(department, 'Missing Department') AS department,
        COUNT(DISTINCT employee_id) AS headcount,
        CASE 
            WHEN COUNT(*) = 0 THEN 1.0
            ELSE 1.0 - (COUNT(CASE WHEN calculated_net_late_minutes > 0 OR missing_punch_count > 0 OR absence_days > 0 THEN 1 END) / CAST(COUNT(*) AS DOUBLE))
        END AS attendance_compliance_pct,
        COALESCE(SUM(absence_days), 0.0) AS absence_days,
        COALESCE(SUM(calculated_late_minutes), 0) AS late_minutes,
        COALESCE(SUM(calculated_net_late_minutes), 0) AS net_late_minutes,
        COALESCE(SUM(missing_punch_count), 0) AS missing_punches,
        COALESCE(SUM(CASE WHEN overtime_approved = TRUE THEN overtime_hours ELSE 0.0 END), 0.0) AS overtime_hours,
        COALESCE((
            SELECT SUM(payroll_ot_cost) 
            FROM base_attendance_payroll_overtime b 
            WHERE b.department = base_expected_attendance.department
        ), 0.0) AS overtime_cost
    FROM base_expected_attendance
    GROUP BY department;
    """)
    print("Created view 'mart_attendance_by_department'")

    # J. Mart View: mart_attendance_late_arrival
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_late_arrival AS
    SELECT 
        employee_id,
        employee_name,
        department,
        project,
        COALESCE(SUM(calculated_late_minutes), 0) AS total_late_minutes,
        COALESCE(SUM(excused_late_minutes), 0) AS total_excused_minutes,
        COALESCE(SUM(calculated_net_late_minutes), 0) AS total_net_late_minutes,
        COUNT(CASE WHEN calculated_late_minutes > 0 THEN 1 END) AS late_arrival_incidents_count
    FROM base_expected_attendance
    GROUP BY employee_id, employee_name, department, project
    HAVING total_late_minutes > 0;
    """)
    print("Created view 'mart_attendance_late_arrival'")

    # K. Mart View: mart_attendance_overtime
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_overtime AS
    SELECT * FROM base_attendance_payroll_overtime;
    """)
    print("Created view 'mart_attendance_overtime'")

    # L. Mart View: mart_attendance_missing_punches
    conn.execute("""
    CREATE OR REPLACE VIEW mart_attendance_missing_punches AS
    SELECT 
        employee_id,
        employee_name,
        department,
        project,
        COUNT(CASE WHEN actual_check_in IS NULL AND actual_check_out IS NOT NULL THEN 1 END) AS missing_check_in_count,
        COUNT(CASE WHEN actual_check_in IS NOT NULL AND actual_check_out IS NULL THEN 1 END) AS missing_check_out_count,
        COALESCE(SUM(missing_punch_count), 0) AS total_missing_punches
    FROM base_expected_attendance
    GROUP BY employee_id, employee_name, department, project
    HAVING total_missing_punches > 0;
    """)
    print("Created view 'mart_attendance_missing_punches'")

    # -------------------------------------------------------------
    # Milestone 2D: Saudization, Compliance & Government Platforms
    # -------------------------------------------------------------
    compliance_rules = rules.get("compliance_rules", {})
    comp_report_month_source = compliance_rules.get("report_month_source", "max_compliance_period")
    has_gosi_source = compliance_rules.get("has_gosi_source_for_period", True)
    has_wps_source = compliance_rules.get("has_wps_source_for_period", True)

    if comp_report_month_source == "max_compliance_period":
        try:
            max_period_row = conn.execute("SELECT MAX(period) FROM compliance").fetchone()
            max_period = max_period_row[0] if max_period_row else None
            if max_period:
                comp_report_month = str(max_period)[:7]
            else:
                comp_report_month = "2026-06"
        except Exception as e:
            print(f"Error querying max compliance period: {e}. Falling back to 2026-06.")
            comp_report_month = "2026-06"
    else:
        comp_report_month = "2026-06"

    print(f"Using compliance report month: {comp_report_month}")
    has_gosi_source_sql = "TRUE" if has_gosi_source else "FALSE"
    has_wps_source_sql = "TRUE" if has_wps_source else "FALSE"

    # 1. Base View: base_government_platform_records
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_government_platform_records AS
    SELECT 
        c.employee_id,
        c.period,
        c.qiwa_status,
        c.gosi_status,
        c.mudad_status,
        c.contract_authenticated,
        c.gosi_salary,
        c.payroll_basic_salary,
        c.occupation_code,
        c.occupation_match_status,
        c.work_permit_expiry,
        c.iqama_expiry,
        c.insurance_status,
        e.employee_name,
        e.status AS employee_status,
        e.is_saudi,
        e.nationality,
        e.project,
        e.department,
        e.cost_center,
        CASE 
            WHEN e.employee_id IS NULL THEN 'Unknown Employee'
            WHEN e.status = 'Active' THEN 'Active Employee'
            WHEN e.status = 'Inactive' THEN 'Inactive Employee'
            WHEN e.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS record_classification
    FROM compliance c
    LEFT JOIN base_employees_deduplicated e ON c.employee_id = e.employee_id
    WHERE c.period = '{comp_report_month}';
    """)
    print("Created view 'base_government_platform_records'")

    # 2. Base View: base_compliance_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_compliance_current AS
    SELECT 
        e.employee_id,
        e.employee_name,
        e.nationality,
        e.is_saudi,
        e.company,
        e.department,
        e.project,
        e.cost_center,
        e.job_title,
        e.employment_type,
        c.qiwa_status,
        c.gosi_status,
        c.mudad_status,
        c.contract_authenticated,
        c.gosi_salary,
        c.payroll_basic_salary,
        c.occupation_code,
        c.occupation_match_status,
        c.work_permit_expiry,
        c.iqama_expiry,
        c.insurance_status
    FROM base_active_workforce e
    LEFT JOIN compliance c ON e.employee_id = c.employee_id AND c.period = '{comp_report_month}';
    """)
    print("Created view 'base_compliance_current'")

    # 3. Base View: base_saudization_population
    conn.execute("""
    CREATE OR REPLACE VIEW base_saudization_population AS
    SELECT 
        employee_id,
        employee_name,
        nationality,
        is_saudi,
        project,
        department,
        CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 ELSE 0 END AS saudi_count,
        CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 ELSE 0 END AS non_saudi_count,
        CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 ELSE 0 END AS missing_nationality_count
    FROM base_active_workforce;
    """)
    print("Created view 'base_saudization_population'")

    # 4. Base View: base_government_status
    conn.execute("""
    CREATE OR REPLACE VIEW base_government_status AS
    SELECT 
        employee_id,
        employee_name,
        is_saudi,
        gosi_status,
        mudad_status AS wps_status,
        gosi_salary,
        payroll_basic_salary,
        CASE WHEN gosi_status IS NOT NULL THEN 1 ELSE 0 END AS has_gosi_source,
        CASE WHEN mudad_status IS NOT NULL THEN 1 ELSE 0 END AS has_wps_source
    FROM base_compliance_current;
    """)
    print("Created view 'base_government_status'")

    # 5. Base View: base_document_expiry
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_document_expiry AS
    WITH anchor AS (
        SELECT last_day(CAST('{comp_report_month}-01' AS DATE)) AS anchor_date
    )
    SELECT 
        e.employee_id,
        e.employee_name,
        e.is_saudi,
        e.iqama_expiry,
        e.work_permit_expiry,
        -- Iqama aging bucket
        CASE 
            WHEN e.iqama_expiry IS NULL THEN 'missing_date'
            WHEN e.iqama_expiry < a.anchor_date THEN 'expired'
            WHEN e.iqama_expiry >= a.anchor_date AND e.iqama_expiry <= a.anchor_date + 30 THEN '0_30'
            WHEN e.iqama_expiry > a.anchor_date + 30 AND e.iqama_expiry <= a.anchor_date + 60 THEN '31_60'
            WHEN e.iqama_expiry > a.anchor_date + 60 AND e.iqama_expiry <= a.anchor_date + 90 THEN '61_90'
            ELSE '90_plus'
        END AS iqama_bucket,
        -- Work Permit aging bucket
        CASE 
            WHEN e.work_permit_expiry IS NULL THEN 'missing_date'
            WHEN e.work_permit_expiry < a.anchor_date THEN 'expired'
            WHEN e.work_permit_expiry >= a.anchor_date AND e.work_permit_expiry <= a.anchor_date + 30 THEN '0_30'
            WHEN e.work_permit_expiry > a.anchor_date + 30 AND e.work_permit_expiry <= a.anchor_date + 60 THEN '31_60'
            WHEN e.work_permit_expiry > a.anchor_date + 60 AND e.work_permit_expiry <= a.anchor_date + 90 THEN '61_90'
            ELSE '90_plus'
        END AS work_permit_bucket
    FROM base_compliance_current e
    CROSS JOIN anchor a
    WHERE e.is_saudi = FALSE AND e.nationality IS NOT NULL AND TRIM(e.nationality) != '';
    """)
    print("Created view 'base_document_expiry'")

    # 6. Mart View: mart_compliance_exceptions
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_compliance_exceptions AS
    -- 1. Active employee missing GOSI status (conditional on GOSI source availability)
    SELECT employee_id, employee_name, 'Missing GOSI Status Record' AS issue_type, 
           'Active employee has no record in GOSI registration field' AS description, 
           'Critical' AS severity, 'Check GOSI enrollment status' AS recommended_action 
    FROM base_compliance_current 
    WHERE gosi_status IS NULL AND {has_gosi_source_sql}
    
    UNION ALL
    
    -- 2. Active employee not registered in GOSI, if status exists
    SELECT employee_id, employee_name, 'Not Registered in GOSI' AS issue_type, 
           'Active employee exists but status is ' || gosi_status AS description, 
           'Critical' AS severity, 'Register employee in GOSI portal' AS recommended_action 
    FROM base_compliance_current 
    WHERE gosi_status IS NOT NULL AND gosi_status != 'Registered'
    
    UNION ALL
    
    -- 3. Active employee missing WPS record (conditional on WPS source availability)
    SELECT employee_id, employee_name, 'Missing WPS Record' AS issue_type, 
           'Active employee has no record in WPS (Mudad) portal' AS description, 
           'Critical' AS severity, 'Add employee to WPS payroll files' AS recommended_action 
    FROM base_compliance_current 
    WHERE mudad_status IS NULL AND {has_wps_source_sql}
    
    UNION ALL
    
    -- 4. Employee appearing in WPS but inactive in workforce (only when WPS status exists)
    SELECT employee_id, employee_name, 'WPS Record for Inactive Employee' AS issue_type, 
           'Employee is appearing in government WPS file with status ' || mudad_status || ' but is inactive/terminated (' || COALESCE(employee_status, 'Unknown') || ')' AS description, 
           'Critical' AS severity, 'Stop WPS payroll entry and verify status' AS recommended_action 
    FROM base_government_platform_records 
    WHERE record_classification != 'Active Employee' AND mudad_status IS NOT NULL
    
    UNION ALL
    
    -- 5. Missing project for compliance population
    SELECT employee_id, employee_name, 'Missing Project assignment' AS issue_type, 
           'Active employee is missing project code assignment' AS description, 
           'Warning' AS severity, 'Update project mapping in master file' AS recommended_action 
    FROM base_active_workforce 
    WHERE project IS NULL OR TRIM(project) = ''
    
    UNION ALL
    
    -- 6. Missing department for compliance population
    SELECT employee_id, employee_name, 'Missing Department assignment' AS issue_type, 
           'Active employee is missing department mapping' AS description, 
           'Warning' AS severity, 'Update department mapping in master file' AS recommended_action 
    FROM base_active_workforce 
    WHERE department IS NULL OR TRIM(department) = ''
    
    UNION ALL
    
    -- 7. Missing cost center for compliance population
    SELECT employee_id, employee_name, 'Missing Cost Center assignment' AS issue_type, 
           'Active employee is missing cost center assignment' AS description, 
           'Warning' AS severity, 'Update cost center in master file' AS recommended_action 
    FROM base_active_workforce 
    WHERE cost_center IS NULL OR TRIM(cost_center) = ''
    
    UNION ALL
    
    -- 8. Missing Qiwa Contract
    SELECT employee_id, employee_name, 'Missing Qiwa Contract' AS issue_type, 
           'Active employee has no contract registered in Qiwa' AS description, 
           'Critical' AS severity, 'Register digital contract in Qiwa portal' AS recommended_action 
    FROM base_compliance_current 
    WHERE qiwa_status IS NULL OR qiwa_status != 'Active'
    
    UNION ALL
    
    -- 9. Contract Not Authenticated
    SELECT employee_id, employee_name, 'Contract Not Authenticated' AS issue_type, 
           'Digital contract is pending employee authentication' AS description, 
           'Warning' AS severity, 'Request employee to log into Qiwa and approve contract' AS recommended_action 
    FROM base_compliance_current 
    WHERE contract_authenticated = FALSE
    
    UNION ALL
    
    -- 10. GOSI Salary Mismatch (excluding nulls)
    SELECT employee_id, employee_name, 'GOSI Salary Mismatch' AS issue_type, 
           'Registered GOSI salary (' || gosi_salary || ') differs from basic salary (' || payroll_basic_salary || ')' AS description, 
           'Critical' AS severity, 'Update GOSI salary records to match payroll basic' AS recommended_action 
    FROM base_compliance_current 
    WHERE gosi_salary IS NOT NULL AND payroll_basic_salary IS NOT NULL AND gosi_salary != payroll_basic_salary
    
    UNION ALL
    
    -- 11. Missing Salary Values in Compliance/Payroll
    SELECT employee_id, employee_name, 'Missing Salary Info' AS issue_type, 
           'Active employee has null salary values in GOSI or payroll base' AS description, 
           'Warning' AS severity, 'Update salary values in GOSI/payroll database' AS recommended_action 
    FROM base_compliance_current 
    WHERE gosi_salary IS NULL OR payroll_basic_salary IS NULL
    
    UNION ALL
    
    -- 12. Occupation Mismatch
    SELECT employee_id, employee_name, 'Occupation Mismatch' AS issue_type, 
           'Qiwa occupational code does not match active role description' AS description, 
           'Warning' AS severity, 'Correct occupational designation code in Qiwa portal' AS recommended_action 
    FROM base_compliance_current 
    WHERE occupation_match_status IS NULL OR occupation_match_status != 'Matched'
    
    UNION ALL
    
    -- 13. Insurance Inactive
    SELECT employee_id, employee_name, 'Insurance Inactive' AS issue_type, 
           'Medical insurance coverage status is not active' AS description, 
           'Critical' AS severity, 'Activate insurance profile in provider database' AS recommended_action 
    FROM base_compliance_current 
    WHERE insurance_status IS NULL OR insurance_status != 'Active'
    
    UNION ALL
    
    -- 14. Missing Nationality / Saudi Status
    SELECT employee_id, employee_name, 'Missing Nationality' AS issue_type, 
           'Active employee has null/missing nationality or Saudization status' AS description, 
           'Warning' AS severity, 'Update employee nationality records in master file' AS recommended_action 
    FROM base_active_workforce 
    WHERE nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL
    
    UNION ALL
    
    -- 15. Non-Saudi employee missing Iqama expiry date
    SELECT employee_id, employee_name, 'Missing Iqama Expiry Date' AS issue_type, 
           'Non-Saudi employee is missing an Iqama expiry date' AS description, 
           'Warning' AS severity, 'Update compliance records with Iqama expiry date' AS recommended_action 
    FROM base_document_expiry 
    WHERE iqama_bucket = 'missing_date'
    
    UNION ALL
    
    -- 16. Non-Saudi employee with expired Iqama
    SELECT employee_id, employee_name, 'Expired Iqama' AS issue_type, 
           'Iqama has expired: ' || COALESCE(CAST(iqama_expiry AS VARCHAR), 'N/A') AS description, 
           'Critical' AS severity, 'Renew Iqama immediately' AS recommended_action 
    FROM base_document_expiry 
    WHERE iqama_bucket = 'expired'
    
    UNION ALL
    
    -- 17. Non-Saudi employee with Iqama expiring within 30 days
    SELECT employee_id, employee_name, 'Iqama Expiring Soon' AS issue_type, 
           'Iqama is expiring within 30 days: ' || COALESCE(CAST(iqama_expiry AS VARCHAR), 'N/A') AS description, 
           'Warning' AS severity, 'Initiate Iqama renewal' AS recommended_action 
    FROM base_document_expiry 
    WHERE iqama_bucket = '0_30'
    
    UNION ALL
    
    -- 18. Non-Saudi employee missing work permit expiry date
    SELECT employee_id, employee_name, 'Missing Work Permit Expiry Date' AS issue_type, 
           'Non-Saudi employee is missing a Work Permit expiry date' AS description, 
           'Warning' AS severity, 'Update compliance records with Work Permit expiry date' AS recommended_action 
    FROM base_document_expiry 
    WHERE work_permit_bucket = 'missing_date'
    
    UNION ALL
    
    -- 19. Non-Saudi employee with expired work permit
    SELECT employee_id, employee_name, 'Expired Work Permit' AS issue_type, 
           'Work permit has expired: ' || COALESCE(CAST(work_permit_expiry AS VARCHAR), 'N/A') AS description, 
           'Critical' AS severity, 'Renew work permit immediately' AS recommended_action 
    FROM base_document_expiry 
    WHERE work_permit_bucket = 'expired'
    
    UNION ALL
    
    -- 20. Non-Saudi employee with work permit expiring within 30 days
    SELECT employee_id, employee_name, 'Work Permit Expiring Soon' AS issue_type, 
           'Work permit is expiring within 30 days: ' || COALESCE(CAST(work_permit_expiry AS VARCHAR), 'N/A') AS description, 
           'Warning' AS severity, 'Initiate work permit renewal' AS recommended_action 
    FROM base_document_expiry 
    WHERE work_permit_bucket = '0_30';
    """)
    print("Created view 'mart_compliance_exceptions'")

    # 7. Mart View: mart_compliance_kpis
    conn.execute("""
    CREATE OR REPLACE VIEW mart_compliance_kpis AS
    WITH counts AS (
        SELECT 
            COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS saudi_hc,
            COUNT(CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS non_saudi_hc,
            COUNT(CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 END) AS missing_nationality
        FROM base_active_workforce
    ),
    expiries AS (
        SELECT 
            COUNT(CASE WHEN iqama_bucket = '0_30' THEN 1 END) AS iqamas_expiring_30,
            COUNT(CASE WHEN iqama_bucket = 'expired' THEN 1 END) AS iqamas_expired,
            COUNT(CASE WHEN work_permit_bucket = '0_30' THEN 1 END) AS work_permits_expiring_30,
            COUNT(CASE WHEN work_permit_bucket = 'expired' THEN 1 END) AS work_permits_expired
        FROM base_document_expiry
    ),
    gosi_wps AS (
        SELECT 
            COUNT(CASE WHEN gosi_status != 'Registered' OR gosi_status IS NULL THEN 1 END) AS gosi_not_registered,
            COUNT(CASE WHEN mudad_status != 'Compliant' OR mudad_status IS NULL THEN 1 END) AS wps_exceptions
        FROM base_compliance_current
    ),
    exc_count AS (
        SELECT COUNT(*) AS exception_count FROM mart_compliance_exceptions
    )
    SELECT 
        c.saudi_hc AS saudi_headcount,
        c.non_saudi_hc AS non_saudi_headcount,
        c.missing_nationality AS employees_missing_nationality,
        CASE 
            WHEN (c.saudi_hc + c.non_saudi_hc) = 0 THEN 0.0
            ELSE ROUND(100.0 * c.saudi_hc / (c.saudi_hc + c.non_saudi_hc), 2)
        END AS saudization_pct,
        e.iqamas_expiring_30,
        e.work_permits_expiring_30,
        e.iqamas_expired,
        e.work_permits_expired,
        gw.gosi_not_registered AS gosi_missing_count,
        gw.wps_exceptions AS wps_exception_count,
        ex.exception_count AS compliance_exception_count
    FROM counts c
    CROSS JOIN expiries e
    CROSS JOIN gosi_wps gw
    CROSS JOIN exc_count ex;
    """)
    print("Created view 'mart_compliance_kpis'")

    # 8. Mart View: mart_saudization_summary
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_saudization_summary AS
    -- Sample-mode simulated history (clearly documented as mock trend history)
    SELECT '2026-04' AS period, 8 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 44.44 AS saudization_pct
    UNION ALL
    SELECT '2026-05' AS period, 9 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 47.37 AS saudization_pct
    UNION ALL
    -- Live dynamic data
    SELECT '{comp_report_month}' AS period, saudi_headcount, non_saudi_headcount, employees_missing_nationality, saudization_pct FROM mart_compliance_kpis;
    """)
    print("Created view 'mart_saudization_summary'")

    # 9. Mart View: mart_saudization_by_project
    conn.execute("""
    CREATE OR REPLACE VIEW mart_saudization_by_project AS
    SELECT 
        COALESCE(project, 'Unassigned') AS project,
        COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS saudi_headcount,
        COUNT(CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS non_saudi_headcount,
        COUNT(CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 END) AS employees_missing_nationality,
        COUNT(*) AS total_headcount,
        CASE 
            WHEN COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END) = 0 THEN 0.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) / COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END), 2)
        END AS saudization_pct
    FROM base_active_workforce
    GROUP BY project;
    """)
    print("Created view 'mart_saudization_by_project'")

    # 10. Mart View: mart_saudization_by_department
    conn.execute("""
    CREATE OR REPLACE VIEW mart_saudization_by_department AS
    SELECT 
        COALESCE(department, 'Unassigned') AS department,
        COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS saudi_headcount,
        COUNT(CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS non_saudi_headcount,
        COUNT(CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 END) AS employees_missing_nationality,
        COUNT(*) AS total_headcount,
        CASE 
            WHEN COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END) = 0 THEN 0.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) / COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END), 2)
        END AS saudization_pct
    FROM base_active_workforce
    GROUP BY department;
    """)
    print("Created view 'mart_saudization_by_department'")

    # 11. Mart View: mart_document_expiry
    conn.execute("""
    CREATE OR REPLACE VIEW mart_document_expiry AS
    SELECT 
        b.expiry_bucket,
        COALESCE(i.cnt, 0) AS iqama_count,
        COALESCE(w.cnt, 0) AS work_permit_count
    FROM (
        SELECT 'expired' AS expiry_bucket
        UNION ALL SELECT '0_30'
        UNION ALL SELECT '31_60'
        UNION ALL SELECT '61_90'
        UNION ALL SELECT '90_plus'
        UNION ALL SELECT 'missing_date'
    ) b
    LEFT JOIN (SELECT iqama_bucket, COUNT(*) AS cnt FROM base_document_expiry GROUP BY iqama_bucket) i ON b.expiry_bucket = i.iqama_bucket
    LEFT JOIN (SELECT work_permit_bucket, COUNT(*) AS cnt FROM base_document_expiry GROUP BY work_permit_bucket) w ON b.expiry_bucket = w.work_permit_bucket;
    """)
    print("Created view 'mart_document_expiry'")

    # 12. Mart View: mart_gosi_status
    conn.execute("""
    CREATE OR REPLACE VIEW mart_gosi_status AS
    SELECT 
        CASE 
            WHEN gosi_status = 'Registered' THEN 'Registered'
            WHEN gosi_status IS NOT NULL THEN 'Not Registered'
            ELSE 'Missing Source / Unknown'
        END AS gosi_status,
        COUNT(*) AS employee_count
    FROM base_compliance_current
    GROUP BY 1;
    """)
    print("Created view 'mart_gosi_status'")

    print("Created view 'mart_wps_status'")

    # -------------------------------------------------------------
    # Milestone 2E: Employee Relations & SLA Dashboard
    # -------------------------------------------------------------
    er_rules = rules.get("er_rules", {})
    er_report_month_source = er_rules.get("report_month_source", "max_case_date")
    er_default_report_month = er_rules.get("default_report_month", "2026-06")
    sla_days_config = er_rules.get("sla_days", {})
    disciplinary_sla_days = sla_days_config.get("Disciplinary", 14)
    grievance_sla_days = sla_days_config.get("Grievance", 10)
    labor_case_sla_days = sla_days_config.get("Labor Case", 30)

    if er_report_month_source == "max_case_date":
        try:
            max_date_row = conn.execute("SELECT MAX(created_date) FROM employee_relations").fetchone()
            max_date = max_date_row[0] if max_date_row else None
            if max_date:
                er_report_month = str(max_date)[:7]
            else:
                er_report_month = er_default_report_month
        except Exception as e:
            print(f"Error querying max case date: {e}. Falling back to default.")
            er_report_month = er_default_report_month
    else:
        er_report_month = er_default_report_month

    print(f"Using ER report month: {er_report_month}")
    report_month_start = f"{er_report_month}-01"
    # Resolve end of month and anchor date dynamically
    report_month_end_date = conn.execute(f"SELECT last_day(CAST('{report_month_start}' AS DATE))").fetchone()[0]
    report_month_end = str(report_month_end_date)
    report_anchor_date = report_month_end

    # 1. Base View: base_er_cases_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_er_cases_current AS
    SELECT 
        row_number() OVER (ORDER BY c.case_id, c.employee_id, c.created_date, c.case_type, c.priority) AS er_case_record_id,
        c.case_id,
        c.employee_id,
        c.case_type,
        c.case_status,
        c.priority,
        c.created_date,
        c.target_due_date,
        c.closed_date,
        c.owner_id,
        c.escalated,
        c.escalation_reason,
        c.legal_reference,
        c.case_number,
        c.description,
        e.employee_name,
        COALESCE(e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unassigned') AS department,
        e.manager_id,
        e.company,
        e.nationality,
        e.job_title,
        e.cost_center,
        CASE 
            WHEN e.employee_id IS NULL THEN 'Unknown Employee'
            WHEN e.status = 'Active' THEN 'Active Employee'
            WHEN e.status = 'Inactive' THEN 'Inactive Employee'
            WHEN e.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS subject_classification
    FROM employee_relations c
    LEFT JOIN base_employees_deduplicated e ON c.employee_id = e.employee_id
    WHERE c.created_date <= '{report_month_end}'
      AND (
          c.closed_date IS NULL 
          OR c.closed_date > '{report_month_end}'
          OR (c.closed_date BETWEEN '{report_month_start}' AND '{report_month_end}')
          OR (c.created_date BETWEEN '{report_month_start}' AND '{report_month_end}')
      );
    """)
    print("Created view 'base_er_cases_current'")

    # 2. Base View: base_er_case_parties
    conn.execute("""
    CREATE OR REPLACE VIEW base_er_case_parties AS
    SELECT 
        c.er_case_record_id,
        c.case_id,
        c.employee_id AS subject_employee_id,
        c.employee_name AS subject_employee_name,
        c.subject_classification,
        c.owner_id AS owner_employee_id,
        eo.employee_name AS owner_employee_name,
        eo.status AS owner_raw_status,
        CASE 
            WHEN c.owner_id IS NULL OR TRIM(c.owner_id) = '' THEN 'Unknown Employee'
            WHEN eo.employee_id IS NULL THEN 'Unknown Employee'
            WHEN eo.status = 'Active' THEN 'Active Employee'
            WHEN eo.status = 'Inactive' THEN 'Inactive Employee'
            WHEN eo.status = 'Terminated' THEN 'Terminated Employee'
            ELSE 'Unknown Status Employee'
        END AS owner_classification
    FROM base_er_cases_current c
    LEFT JOIN base_employees_deduplicated eo ON c.owner_id = eo.employee_id;
    """)
    print("Created view 'base_er_case_parties'")

    # 3. Base View: base_hr_requests_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_hr_requests_current AS
    SELECT 
        r.request_id,
        r.employee_id,
        r.request_type,
        r.request_status,
        r.created_at,
        r.closed_at,
        r.owner AS owner_id,
        r.sla_hours,
        r.actual_hours,
        r.sla_breached,
        COALESCE(r.project, e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unassigned') AS department
    FROM hr_requests r
    LEFT JOIN base_employees_deduplicated e ON r.employee_id = e.employee_id
    WHERE r.created_at <= '{report_month_end} 23:59:59'
      AND (r.closed_at IS NULL OR r.closed_at >= '{report_month_start} 00:00:00');
    """)
    print("Created view 'base_hr_requests_current'")

    # 4. Base View: base_case_sla_clock
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_case_sla_clock AS
    WITH er_sla_prep AS (
        SELECT 
            c.er_case_record_id,
            c.created_date,
            c.closed_date,
            c.case_type,
            c.case_status,
            c.target_due_date,
            CASE 
                WHEN c.case_type = 'Disciplinary' THEN {disciplinary_sla_days}
                WHEN c.case_type = 'Grievance' THEN {grievance_sla_days}
                WHEN c.case_type = 'Labor Case' THEN {labor_case_sla_days}
                ELSE 14
            END AS config_sla_days
        FROM base_er_cases_current c
    ),
    er_sla_effective AS (
        SELECT 
            er_case_record_id,
            case_status,
            created_date,
            closed_date,
            COALESCE(target_due_date, created_date + config_sla_days) AS effective_target_due_date
        FROM er_sla_prep
    )
    SELECT 
        'ER' AS source_type,
        er_case_record_id AS record_id,
        effective_target_due_date AS effective_due_date,
        CASE 
            WHEN closed_date IS NOT NULL THEN (closed_date - created_date)
            ELSE ('{report_anchor_date}' - created_date)
        END AS aging_days,
        CASE 
            WHEN created_date IS NULL OR effective_target_due_date IS NULL THEN 'Not Eligible'
            WHEN closed_date IS NOT NULL AND closed_date <= effective_target_due_date THEN 'Compliant'
            WHEN closed_date IS NOT NULL AND closed_date > effective_target_due_date THEN 'Breached'
            WHEN closed_date IS NULL AND '{report_anchor_date}' > effective_target_due_date THEN 'Breached'
            ELSE 'Pending'
        END AS sla_status
    FROM er_sla_effective

    UNION ALL

    SELECT 
        'HR_REQ' AS source_type,
        request_id AS record_id,
        NULL AS effective_due_date,
        CASE 
            WHEN closed_at IS NOT NULL THEN (CAST(closed_at AS DATE) - CAST(created_at AS DATE))
            ELSE ('{report_anchor_date}' - CAST(created_at AS DATE))
        END AS aging_days,
        CASE 
            WHEN sla_hours IS NULL THEN 'Not Eligible'
            WHEN actual_hours <= sla_hours THEN 'Compliant'
            ELSE 'Breached'
        END AS sla_status
    FROM base_hr_requests_current;
    """)
    print("Created view 'base_case_sla_clock'")

    # 5. Base View: base_er_case_population
    conn.execute("""
    CREATE OR REPLACE VIEW base_er_case_population AS
    SELECT 
        c.*, 
        s.aging_days, 
        s.sla_status,
        s.effective_due_date AS effective_target_due_date
    FROM base_er_cases_current c
    JOIN base_case_sla_clock s ON c.er_case_record_id = s.record_id AND s.source_type = 'ER';
    """)
    print("Created view 'base_er_case_population'")

    # 6. Mart View: mart_er_exceptions
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_er_exceptions AS
    -- 1. Open case missing owner
    SELECT case_id, employee_name, 'Missing Case Owner' AS issue_type, 'Open case has no owner assigned' AS description, 'Critical' AS severity, 'Assign an owner to investigate' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (owner_id IS NULL OR TRIM(owner_id) = '')
    UNION ALL
    -- 2. Open case missing project
    SELECT case_id, employee_name, 'Missing Project' AS issue_type, 'Open case has no project link' AS description, 'Warning' AS severity, 'Update subject employee project assignment' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (project = 'Unassigned' OR project IS NULL)
    UNION ALL
    -- 3. Open case missing department
    SELECT case_id, employee_name, 'Missing Department' AS issue_type, 'Open case has no department link' AS description, 'Warning' AS severity, 'Update subject employee department assignment' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (department = 'Unassigned' OR department IS NULL)
    UNION ALL
    -- 4. Open case missing case type
    SELECT case_id, employee_name, 'Missing Case Type' AS issue_type, 'Case type is blank' AS description, 'Critical' AS severity, 'Specify Grievance, Disciplinary, or Labor Case' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (case_type IS NULL OR TRIM(case_type) = '')
    UNION ALL
    -- 5. Open case missing priority
    SELECT case_id, employee_name, 'Missing Priority' AS issue_type, 'Case priority is blank' AS description, 'Warning' AS severity, 'Set priority level to High, Medium, or Low' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND (priority IS NULL OR TRIM(priority) = '')
    UNION ALL
    -- 6. Open case missing target due date
    SELECT case_id, employee_name, 'Missing Target Due Date' AS issue_type, 'Target due date is blank in source records' AS description, 'Critical' AS severity, 'Set target due date based on SLA rules' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND target_due_date IS NULL
    UNION ALL
    -- 7. Open case overdue
    SELECT case_id, employee_name, 'Overdue Open Case' AS issue_type, 'Open case has breached its effective target due date: ' || CAST(effective_target_due_date AS VARCHAR), 'Critical' AS severity, 'Expedite investigation and case resolution' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND '{report_anchor_date}' > effective_target_due_date
    UNION ALL
    -- 8. Closed case missing closure date
    SELECT case_id, employee_name, 'Missing Closure Date' AS issue_type, 'Case is status Closed but has no closed_date', 'Critical' AS severity, 'Fill closed_date in log' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_status = 'Closed' AND closed_date IS NULL
    UNION ALL
    -- 9. Closed case with closure date before creation date
    SELECT case_id, employee_name, 'Invalid Date Range' AS issue_type, 'Case closed_date (' || COALESCE(CAST(closed_date AS VARCHAR), 'N/A') || ') is before created_date (' || CAST(created_date AS VARCHAR) || ')', 'Critical' AS severity, 'Correct date entries' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE closed_date IS NOT NULL AND closed_date < created_date
    UNION ALL
    -- 10. Case assigned to inactive owner
    SELECT cp.case_id, cp.owner_employee_name, 'Inactive Case Owner' AS issue_type, 'Case investigator owner is classified as: ' || cp.owner_classification, 'Warning' AS severity, 'Reassign case owner to active employee' AS recommended_action, cp.er_case_record_id
    FROM base_er_case_parties cp WHERE cp.owner_classification IN ('Inactive Employee', 'Terminated Employee', 'Unknown Employee')
    UNION ALL
    -- 11. Case linked to inactive employee
    SELECT cp.case_id, cp.subject_employee_name, 'Inactive Case Subject' AS issue_type, 'Case subject employee is classified as: ' || cp.subject_classification, 'Warning' AS severity, 'Check if case is archive or needs resolution closure' AS recommended_action, cp.er_case_record_id
    FROM base_er_case_parties cp WHERE cp.subject_classification IN ('Inactive Employee', 'Terminated Employee')
    UNION ALL
    -- 12. Duplicate case ID
    SELECT case_id, employee_name, 'Duplicate Case ID' AS issue_type, 'Case ID is logged more than once', 'Critical' AS severity, 'Deduplicate ER logs' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_id IN (SELECT case_id FROM base_er_case_population GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 13. SLA status missing
    SELECT case_id, employee_name, 'Missing SLA Status' AS issue_type, 'SLA compliance clock cannot evaluate status', 'Warning' AS severity, 'Provide created_date and target_due_date' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE sla_status = 'Not Eligible'
    UNION ALL
    -- 14. Escalated case missing escalation reason
    SELECT case_id, employee_name, 'Missing Escalation Reason' AS issue_type, 'Case is flagged escalated but reason is blank', 'Warning' AS severity, 'Document reason for case escalation' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE escalated = TRUE AND (escalation_reason IS NULL OR TRIM(escalation_reason) = '')
    UNION ALL
    -- 15. Labor case missing legal reference or case number
    SELECT case_id, employee_name, 'Missing Legal Reference' AS issue_type, 'Labor case is missing court case number or reference log', 'Warning' AS severity, 'Enter legal case details' AS recommended_action, er_case_record_id
    FROM base_er_case_population WHERE case_type = 'Labor Case' AND (legal_reference IS NULL OR TRIM(legal_reference) = '' OR case_number IS NULL OR TRIM(case_number) = '');
    """)
    print("Created view 'mart_er_exceptions'")

    # 7. Mart View: mart_er_kpis
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_er_kpis AS
    WITH er_counts AS (
        SELECT 
            COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') THEN 1 END) AS open_cases,
            COUNT(CASE WHEN created_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS new_cases,
            COUNT(CASE WHEN closed_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS closed_cases,
            ROUND(AVG(aging_days), 1) AS avg_aging,
            COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') AND '{report_anchor_date}' > effective_target_due_date THEN 1 END) AS overdue_cases,
            COUNT(CASE WHEN case_type = 'Disciplinary' THEN 1 END) AS disciplinary_cases,
            COUNT(CASE WHEN case_type = 'Grievance' THEN 1 END) AS grievance_cases,
            COUNT(CASE WHEN case_type = 'Labor Case' THEN 1 END) AS labor_cases,
            COUNT(CASE WHEN escalated = TRUE THEN 1 END) AS escalated_cases
        FROM base_er_case_population
    ),
    er_sla AS (
        SELECT 
            ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / 
                  NULLIF(COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 0), 2) AS er_sla_compliance
        FROM base_er_case_population
    ),
    exc AS (
        SELECT COUNT(*) AS exception_count FROM mart_er_exceptions
    )
    SELECT 
        c.open_cases AS total_open_er_cases,
        c.new_cases AS new_cases_this_month,
        c.closed_cases AS closed_cases_this_month,
        COALESCE(c.avg_aging, 0.0) AS average_case_aging_days,
        c.overdue_cases AS overdue_cases,
        COALESCE(s.er_sla_compliance, 100.0) AS sla_compliance_pct,
        c.disciplinary_cases AS disciplinary_cases,
        c.grievance_cases AS grievance_cases,
        c.labor_cases AS labor_cases,
        c.escalated_cases AS escalated_cases,
        ex.exception_count AS er_exception_count
    FROM er_counts c
    CROSS JOIN er_sla s
    CROSS JOIN exc ex;
    """)
    print("Created view 'mart_er_kpis'")

    # 8. Mart View: mart_er_case_trend
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_er_case_trend AS
    -- Simulated historical trend for MVP visuals
    SELECT '2026-04' AS period, 4 AS new_cases, 3 AS closed_cases
    UNION ALL
    SELECT '2026-05' AS period, 5 AS new_cases, 4 AS closed_cases
    UNION ALL
    -- Live dynamic current period
    SELECT 
        '{er_report_month}' AS period,
        COUNT(CASE WHEN created_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS new_cases,
        COUNT(CASE WHEN closed_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS closed_cases
    FROM base_er_case_population;
    """)
    print("Created view 'mart_er_case_trend'")

    # 9. Mart View: mart_er_cases_by_project
    conn.execute("""
    CREATE OR REPLACE VIEW mart_er_cases_by_project AS
    SELECT 
        project,
        COUNT(*) AS total_cases,
        COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') THEN 1 END) AS open_cases,
        COUNT(CASE WHEN case_status = 'Closed' THEN 1 END) AS closed_cases,
        COUNT(CASE WHEN escalated = TRUE THEN 1 END) AS escalated_cases,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_cases,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM base_er_case_population
    GROUP BY project;
    """)
    print("Created view 'mart_er_cases_by_project'")

    # 10. Mart View: mart_er_cases_by_department
    conn.execute("""
    CREATE OR REPLACE VIEW mart_er_cases_by_department AS
    SELECT 
        department,
        COUNT(*) AS total_cases,
        COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') THEN 1 END) AS open_cases,
        COUNT(CASE WHEN case_status = 'Closed' THEN 1 END) AS closed_cases,
        COUNT(CASE WHEN escalated = TRUE THEN 1 END) AS escalated_cases,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_cases,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM base_er_case_population
    GROUP BY department;
    """)
    print("Created view 'mart_er_cases_by_department'")

    # 11. Mart View: mart_er_case_type_distribution
    conn.execute("""
    CREATE OR REPLACE VIEW mart_er_case_type_distribution AS
    SELECT 
        case_type,
        COUNT(*) AS case_count
    FROM base_er_case_population
    GROUP BY case_type;
    """)
    print("Created view 'mart_er_case_type_distribution'")

    # 12. Mart View: mart_er_case_status_distribution
    conn.execute("""
    CREATE OR REPLACE VIEW mart_er_case_status_distribution AS
    SELECT 
        case_status,
        COUNT(*) AS case_count
    FROM base_er_case_population
    GROUP BY case_status;
    """)
    print("Created view 'mart_er_case_status_distribution'")

    # 13. Mart View: mart_er_sla_performance
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_er_sla_performance AS
    SELECT 
        'ER' AS category_type,
        case_type AS category,
        COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) AS eligible_count,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_count,
        COUNT(CASE WHEN sla_status = 'Breached' THEN 1 END) AS breached_count,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM base_er_case_population
    GROUP BY 1, 2
    
    UNION ALL
    
    SELECT 
        'HR_REQ' AS category_type,
        request_type AS category,
        COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) AS eligible_count,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_count,
        COUNT(CASE WHEN sla_status = 'Breached' THEN 1 END) AS breached_count,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM (
        SELECT r.*, s.sla_status 
        FROM base_hr_requests_current r
        JOIN base_case_sla_clock s ON r.request_id = s.record_id AND s.source_type = 'HR_REQ'
    )
    GROUP BY 1, 2;
    """)
    print("Created view 'mart_er_sla_performance'")

    # 14. Mart View: mart_er_aging_buckets
    conn.execute("""
    CREATE OR REPLACE VIEW mart_er_aging_buckets AS
    SELECT 
        CASE 
            WHEN aging_days BETWEEN 0 AND 3 THEN '0_3_days'
            WHEN aging_days BETWEEN 4 AND 7 THEN '4_7_days'
            WHEN aging_days BETWEEN 8 AND 14 THEN '8_14_days'
            WHEN aging_days BETWEEN 15 AND 30 THEN '15_30_days'
            ELSE '30_plus_days'
        END AS aging_bucket,
        COUNT(*) AS case_count
    FROM base_er_case_population
    WHERE case_status IN ('Open', 'In Progress', 'Pending')
    GROUP BY 1;
    """)
    print("Created view 'mart_er_aging_buckets'")

    # -------------------------------------------------------------
    # Milestone 2F: Recruitment & Workforce Planning Dashboard
    # -------------------------------------------------------------
    rec_rules = rules.get("recruitment_rules", {})
    rec_report_month_source = rec_rules.get("recruitment_rules", {}).get("report_month_source", "max_requisition_date")
    rec_default_report_month = rec_rules.get("default_report_month", "2026-06")
    default_sla_days = rec_rules.get("default_sla_days", 45)

    if rec_report_month_source == "max_requisition_date":
        try:
            max_date_row = conn.execute("SELECT MAX(approval_date) FROM recruitment_requisitions").fetchone()
            max_date = max_date_row[0] if max_date_row else None
            if max_date:
                rec_report_month = str(max_date)[:7]
            else:
                rec_report_month = rec_default_report_month
        except Exception as e:
            print(f"Error querying max approval date: {e}. Falling back to default.")
            rec_report_month = rec_default_report_month
    else:
        rec_report_month = rec_default_report_month

    print(f"Using Recruitment report month: {rec_report_month}")
    report_month_start = f"{rec_report_month}-01"
    # Resolve end of month and anchor date dynamically
    report_month_end_date = conn.execute(f"SELECT last_day(CAST('{report_month_start}' AS DATE))").fetchone()[0]
    report_month_end = str(report_month_end_date)
    report_anchor_date = report_month_end

    # 1. Source-Level View: base_requisition_source_records
    conn.execute("""
    CREATE OR REPLACE VIEW base_requisition_source_records AS
    SELECT 
        row_number() OVER (ORDER BY requisition_id, job_title, department, project, cost_center, owner_id, approval_date) AS requisition_record_id,
        requisition_id,
        job_title,
        department,
        project,
        cost_center,
        owner_id AS recruiter_id,
        approval_date,
        target_hire_date,
        closed_date,
        status
    FROM recruitment_requisitions;
    """)
    print("Created view 'base_requisition_source_records'")

    # 2. Source-Level View: base_candidate_source_records
    conn.execute("""
    CREATE OR REPLACE VIEW base_candidate_source_records AS
    SELECT 
        row_number() OVER (ORDER BY candidate_id, candidate_name, requisition_id, applied_date) AS candidate_record_id,
        candidate_id,
        candidate_name,
        CASE 
            WHEN source IN ('LinkedIn', 'Indeed', 'Referral', 'Direct', 'Agency') THEN source
            ELSE 'Other'
        END AS source,
        source AS raw_source,
        pipeline_stage,
        requisition_id,
        applied_date
    FROM candidates;
    """)
    print("Created view 'base_candidate_source_records'")

    # 3. Source-Level View: base_interview_source_records
    conn.execute("""
    CREATE OR REPLACE VIEW base_interview_source_records AS
    SELECT 
        row_number() OVER (ORDER BY interview_id, candidate_id, interview_date) AS interview_record_id,
        interview_id,
        candidate_id,
        interview_date,
        recruiter_id AS interviewer_id,
        rating,
        outcome
    FROM interviews;
    """)
    print("Created view 'base_interview_source_records'")

    # 4. Source-Level View: base_offer_source_records
    conn.execute("""
    CREATE OR REPLACE VIEW base_offer_source_records AS
    SELECT 
        row_number() OVER (ORDER BY offer_id, candidate_id, offer_date) AS offer_record_id,
        offer_id,
        candidate_id,
        offer_date,
        salary,
        outcome_status AS offer_status,
        outcome_date
    FROM offers;
    """)
    print("Created view 'base_offer_source_records'")

    # 5. Source-Level View: base_onboarding_source_records
    conn.execute("""
    CREATE OR REPLACE VIEW base_onboarding_source_records AS
    SELECT 
        row_number() OVER (ORDER BY onboarding_id, candidate_id, start_date) AS onboarding_record_id,
        onboarding_id,
        candidate_id,
        start_date AS hire_date,
        status,
        employee_id
    FROM onboarding;
    """)
    print("Created view 'base_onboarding_source_records'")

    # 6. Base View: base_recruitment_requisitions_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_recruitment_requisitions_current AS
    SELECT 
        *,
        COALESCE(target_hire_date, approval_date + {default_sla_days}) AS effective_target_hire_date
    FROM base_requisition_source_records
    WHERE approval_date <= '{report_month_end}'
      AND (
          status IN ('Open', 'Approved', 'In Progress', 'On Hold')
          OR closed_date > '{report_month_end}'
          OR (closed_date BETWEEN '{report_month_start}' AND '{report_month_end}')
          OR (approval_date BETWEEN '{report_month_start}' AND '{report_month_end}')
      )
      AND status NOT IN ('Cancelled', 'Rejected', 'Draft');
    """)
    print("Created view 'base_recruitment_requisitions_current'")

    # 7. Base View: base_candidate_canonical
    conn.execute("""
    CREATE OR REPLACE VIEW base_candidate_canonical AS
    SELECT * EXCLUDE (rn)
    FROM (
        SELECT *,
               row_number() OVER (PARTITION BY candidate_id ORDER BY applied_date DESC, candidate_record_id DESC) AS rn
        FROM base_candidate_source_records
    )
    WHERE rn = 1;
    """)
    print("Created view 'base_candidate_canonical'")

    # 8. Base View: base_candidate_pipeline_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_candidate_pipeline_current AS
    SELECT c.*
    FROM base_candidate_canonical c
    JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
    WHERE c.applied_date <= '{report_month_end}';
    """)
    print("Created view 'base_candidate_pipeline_current'")

    # 9. Base View: base_interview_activity_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_interview_activity_current AS
    SELECT i.*
    FROM base_interview_source_records i
    JOIN base_candidate_canonical c ON i.candidate_id = c.candidate_id
    JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
    WHERE i.interview_date BETWEEN '{report_month_start}' AND '{report_month_end} 23:59:59';
    """)
    print("Created view 'base_interview_activity_current'")

    # 10. Base View: base_offer_activity_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_offer_activity_current AS
    SELECT o.*
    FROM base_offer_source_records o
    JOIN base_candidate_canonical c ON o.candidate_id = c.candidate_id
    JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
    WHERE o.offer_date BETWEEN '{report_month_start}' AND '{report_month_end}';
    """)
    print("Created view 'base_offer_activity_current'")

    # 11. Base View: base_onboarding_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_onboarding_current AS
    SELECT ob.*
    FROM base_onboarding_source_records ob
    JOIN base_candidate_canonical c ON ob.candidate_id = c.candidate_id
    JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
    WHERE ob.hire_date BETWEEN '{report_month_start}' AND '{report_month_end}';
    """)
    print("Created view 'base_onboarding_current'")

    # 12. Base View: base_workforce_plan_current
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_workforce_plan_current AS
    SELECT *
    FROM workforce_plan
    WHERE period = '{rec_report_month}';
    """)
    print("Created view 'base_workforce_plan_current'")

    # 13. Base View: base_vacancy_population
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_vacancy_population AS
    SELECT *
    FROM vacancy_requests
    WHERE status = 'Approved'
      AND approved_date <= '{report_month_end}';
    """)
    print("Created view 'base_vacancy_population'")

    # 14. Mart View: mart_recruitment_exceptions
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_recruitment_exceptions AS
    -- 1. Open requisition missing recruiter
    SELECT requisition_id AS record_id_str, 'Missing Recruiter' AS issue_type, 'Open requisition has no owner recruiter assigned' AS description, 'Critical' AS severity, 'Assign a recruiter' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (recruiter_id IS NULL OR TRIM(recruiter_id) = '')
    UNION ALL
    -- 2. Open requisition missing project
    SELECT requisition_id AS record_id_str, 'Missing Project' AS issue_type, 'Open requisition has no project assignment' AS description, 'Warning' AS severity, 'Assign a project code' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (project = 'Unassigned' OR project IS NULL)
    UNION ALL
    -- 3. Open requisition missing department
    SELECT requisition_id AS record_id_str, 'Missing Department' AS issue_type, 'Open requisition has no department' AS description, 'Warning' AS severity, 'Assign a department' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (department = 'Unassigned' OR department IS NULL)
    UNION ALL
    -- 4. Open requisition missing cost center
    SELECT requisition_id AS record_id_str, 'Missing Cost Center' AS issue_type, 'Open requisition has no cost center' AS description, 'Warning' AS severity, 'Assign a cost center' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (cost_center IS NULL OR TRIM(cost_center) = '')
    UNION ALL
    -- 5. Open requisition missing job title
    SELECT requisition_id AS record_id_str, 'Missing Job Title' AS issue_type, 'Open requisition job title is blank' AS description, 'Critical' AS severity, 'Enter job title' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND (job_title IS NULL OR TRIM(job_title) = '')
    UNION ALL
    -- 6. Open requisition missing target hire date
    SELECT requisition_id AS record_id_str, 'Missing Target Hire Date' AS issue_type, 'Open requisition target hire date is blank' AS description, 'Warning' AS severity, 'Provide target hire date' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND target_hire_date IS NULL
    UNION ALL
    -- 7. Requisition overdue
    SELECT requisition_id AS record_id_str, 'Overdue Requisition' AS issue_type, 'Open requisition has breached its effective target date: ' || CAST(effective_target_hire_date AS VARCHAR), 'Critical' AS severity, 'Expedite sourcing and pipeline conversions' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND '{report_anchor_date}' > effective_target_hire_date
    UNION ALL
    -- 8. Requisition approved but no candidates
    SELECT requisition_id AS record_id_str, 'Empty Candidate Pipeline' AS issue_type, 'Requisition is open but has 0 candidates linked', 'Warning' AS severity, 'Source and link candidates to requisition' AS recommended_action
    FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND requisition_id NOT IN (SELECT DISTINCT requisition_id FROM base_candidate_pipeline_current)
    UNION ALL
    -- 9. Candidate missing pipeline stage
    SELECT candidate_id AS record_id_str, 'Missing Pipeline Stage' AS issue_type, 'Candidate application has no pipeline stage logged', 'Warning' AS severity, 'Assign current pipeline stage' AS recommended_action
    FROM base_candidate_canonical WHERE pipeline_stage IS NULL OR TRIM(pipeline_stage) = ''
    UNION ALL
    -- 10. Candidate linked to unknown requisition
    SELECT candidate_id AS record_id_str, 'Unknown Requisition Link' AS issue_type, 'Candidate is linked to requisition ID ' || COALESCE(requisition_id, 'N/A') || ' which does not exist in master requisitions table', 'Critical' AS severity, 'Link candidate to active requisition' AS recommended_action
    FROM base_candidate_source_records WHERE requisition_id NOT IN (SELECT DISTINCT requisition_id FROM base_requisition_source_records)
    UNION ALL
    -- 11. Interview scheduled without interviewer
    SELECT interview_id AS record_id_str, 'Missing Interviewer' AS issue_type, 'Interview has no interviewer assigned', 'Warning' AS severity, 'Assign interviewer employee ID' AS recommended_action
    FROM base_interview_source_records WHERE (interviewer_id IS NULL OR TRIM(interviewer_id) = '')
    UNION ALL
    -- 12. Interview scheduled without date/time
    SELECT interview_id AS record_id_str, 'Missing Interview Date' AS issue_type, 'Interview record has no scheduled date and time', 'Warning' AS severity, 'Set scheduled interview timestamp' AS recommended_action
    FROM base_interview_source_records WHERE interview_date IS NULL
    UNION ALL
    -- 13. Offer extended without salary
    SELECT offer_id AS record_id_str, 'Offer Missing Salary' AS issue_type, 'Offer extended has no base salary details', 'Critical' AS severity, 'Enter base salary details' AS recommended_action
    FROM base_offer_source_records WHERE salary IS NULL OR salary <= 0
    UNION ALL
    -- 14. Offer accepted but onboarding not started
    SELECT o.offer_id AS record_id_str, 'Onboarding Not Triggered' AS issue_type, 'Offer status is Accepted but onboarding is not logged', 'Critical' AS severity, 'Create onboarding record' AS recommended_action
    FROM base_offer_source_records o WHERE o.offer_status = 'Accepted' AND o.candidate_id NOT IN (SELECT DISTINCT candidate_id FROM base_onboarding_source_records)
    UNION ALL
    -- 15. Onboarding linked to unknown employee
    SELECT onboarding_id AS record_id_str, 'Unknown Employee ID' AS issue_type, 'Onboarding record links to employee ID ' || COALESCE(employee_id, 'N/A') || ' which is missing from employee directory', 'Warning' AS severity, 'Verify active employee ID and link' AS recommended_action
    FROM base_onboarding_source_records WHERE employee_id IS NOT NULL AND employee_id NOT IN (SELECT DISTINCT employee_id FROM base_employees_deduplicated)
    UNION ALL
    -- 16. Duplicate requisition ID
    SELECT requisition_id AS record_id_str, 'Duplicate Requisition ID' AS issue_type, 'Requisition ID is logged multiple times in source records', 'Critical' AS severity, 'Deduplicate requisition records' AS recommended_action
    FROM base_requisition_source_records WHERE requisition_id IN (SELECT requisition_id FROM base_requisition_source_records GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 17. Duplicate candidate ID
    SELECT candidate_id AS record_id_str, 'Duplicate Candidate ID' AS issue_type, 'Candidate ID is logged multiple times in source records', 'Critical' AS severity, 'Deduplicate candidate records' AS recommended_action
    FROM base_candidate_source_records WHERE candidate_id IN (SELECT candidate_id FROM base_candidate_source_records GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 18. Workforce plan missing project or department
    SELECT 'Plan_Row' AS record_id_str, 'Missing Plan Dimension' AS issue_type, 'Workforce plan record has null project or department', 'Warning' AS severity, 'Specify project and department details' AS recommended_action
    FROM base_workforce_plan_current WHERE project IS NULL OR TRIM(project) = '' OR department IS NULL OR TRIM(department) = ''
    UNION ALL
    -- 19. Actual headcount greater than planned headcount
    SELECT COALESCE(wp.project, 'Unassigned') || '-' || COALESCE(wp.department, 'Unassigned') AS record_id_str, 'Plan Exceeded' AS issue_type, 'Actual headcount (' || CAST(COALESCE(ahc.actual_count, 0) AS VARCHAR) || ') exceeds planned headcount (' || CAST(wp.planned_headcount AS VARCHAR) || ')', 'Warning' AS severity, 'Review project hiring plan' AS recommended_action
    FROM base_workforce_plan_current wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM base_active_workforce
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department
    WHERE COALESCE(ahc.actual_count, 0) > wp.planned_headcount
    UNION ALL
    -- 20. Planned headcount not fulfilled by target date
    SELECT COALESCE(wp.project, 'Unassigned') || '-' || COALESCE(wp.department, 'Unassigned') AS record_id_str, 'Plan Unfulfilled' AS issue_type, 'Planned headcount (' || CAST(wp.planned_headcount AS VARCHAR) || ') has not been fulfilled (Actual: ' || CAST(COALESCE(ahc.actual_count, 0) AS VARCHAR) || ') by target date ' || '{report_month_end}', 'Warning' AS severity, 'Expedite hiring pipeline' AS recommended_action
    FROM base_workforce_plan_current wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM base_active_workforce
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department
    WHERE COALESCE(ahc.actual_count, 0) < wp.planned_headcount
    UNION ALL
    -- 21. Null or negative vacancy quantity
    SELECT request_id AS record_id_str, 'Invalid Vacancy Quantity' AS issue_type, 'Vacancy request Approved has invalid quantity: ' || COALESCE(CAST(quantity AS VARCHAR), 'NULL'), 'Critical' AS severity, 'Enter positive quantity' AS recommended_action
    FROM base_vacancy_population WHERE quantity IS NULL OR quantity <= 0
    UNION ALL
    -- 22. Unknown candidate source channel
    SELECT candidate_id AS record_id_str, 'Unknown Source Channel' AS issue_type, 'Candidate has un-normalized source channel: ' || COALESCE(raw_source, 'NULL'), 'Warning' AS severity, 'Update to standard channel' AS recommended_action
    FROM base_candidate_source_records WHERE raw_source NOT IN ('LinkedIn', 'Indeed', 'Referral', 'Direct', 'Agency');
    """)
    print("Created view 'mart_recruitment_exceptions'")

    # 15. Mart View: mart_recruitment_kpis
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_recruitment_kpis AS
    WITH req_stats AS (
        SELECT 
            COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS open_reqs,
            COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND '{report_anchor_date}' > effective_target_hire_date THEN 1 END) AS overdue_reqs
        FROM base_recruitment_requisitions_current
    ),
    vac_stats AS (
        SELECT COALESCE(SUM(quantity), 0) AS approved_vacancies
        FROM base_vacancy_population
    ),
    cand_stats AS (
        SELECT COUNT(*) AS cand_in_pipeline
        FROM base_candidate_pipeline_current
    ),
    int_stats AS (
        SELECT COUNT(*) AS interviews_scheduled
        FROM base_interview_activity_current
    ),
    off_stats AS (
        SELECT 
            COUNT(*) AS offers_extended,
            COUNT(CASE WHEN offer_status = 'Accepted' THEN 1 END) AS accepted_offers,
            COUNT(CASE WHEN offer_status IN ('Accepted', 'Rejected', 'Declined') THEN 1 END) AS decided_offers
        FROM base_offer_activity_current
    ),
    hire_stats AS (
        SELECT COUNT(*) AS hires_this_month
        FROM base_onboarding_current
    ),
    ttf_stats AS (
        SELECT 
            COALESCE(ROUND(AVG(ob.hire_date - r.approval_date), 1), 0.0) AS avg_time_to_fill
        FROM base_onboarding_source_records ob
        JOIN base_candidate_canonical c ON ob.candidate_id = c.candidate_id
        JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
        WHERE ob.hire_date IS NOT NULL AND r.approval_date IS NOT NULL
    ),
    plan_fulfillment AS (
        SELECT 
            CASE 
                WHEN planned.total_planned = 0 THEN 
                    CASE WHEN actual.total_actual = 0 THEN 100.0 ELSE 0.0 END
                ELSE ROUND(100.0 * actual.total_actual / planned.total_planned, 2)
            END AS plan_fulfillment_pct
        FROM (
            SELECT COALESCE(SUM(planned_headcount), 0) AS total_planned 
            FROM base_workforce_plan_current
        ) planned
        CROSS JOIN (
            SELECT COUNT(aw.employee_id) AS total_actual
            FROM base_workforce_plan_current wp
            LEFT JOIN base_active_workforce aw ON wp.project = aw.project AND wp.department = aw.department
        ) actual
    ),
    exc_stats AS (
        SELECT COUNT(*) AS exception_count FROM mart_recruitment_exceptions
    )
    SELECT 
        r.open_reqs AS open_requisitions,
        v.approved_vacancies AS approved_vacancies,
        c.cand_in_pipeline AS candidates_in_pipeline,
        i.interviews_scheduled AS interviews_scheduled,
        o.offers_extended AS offers_extended,
        CASE 
            WHEN o.decided_offers = 0 THEN 100.0
            ELSE ROUND(100.0 * o.accepted_offers / o.decided_offers, 2)
        END AS offer_acceptance_pct,
        h.hires_this_month AS hires_this_month,
        t.avg_time_to_fill AS average_time_to_fill,
        r.overdue_reqs AS overdue_requisitions,
        COALESCE(p.plan_fulfillment_pct, 100.0) AS workforce_plan_fulfillment_pct,
        ex.exception_count AS recruitment_exception_count
    FROM req_stats r
    CROSS JOIN vac_stats v
    CROSS JOIN cand_stats c
    CROSS JOIN int_stats i
    CROSS JOIN off_stats o
    CROSS JOIN hire_stats h
    CROSS JOIN ttf_stats t
    CROSS JOIN plan_fulfillment p
    CROSS JOIN exc_stats ex;
    """)
    print("Created view 'mart_recruitment_kpis'")

    # 16. Mart View: mart_recruitment_pipeline
    conn.execute("""
    CREATE OR REPLACE VIEW mart_recruitment_pipeline AS
    SELECT 
        pipeline_stage,
        COUNT(*) AS candidate_count
    FROM base_candidate_pipeline_current
    GROUP BY pipeline_stage;
    """)
    print("Created view 'mart_recruitment_pipeline'")

    # 17. Mart View: mart_recruitment_trends
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_recruitment_trends AS
    -- Simulated historical trend for MVP visuals
    SELECT '2026-04' AS period, 5 AS requisitions_opened, 3 AS hires
    UNION ALL
    SELECT '2026-05' AS period, 6 AS requisitions_opened, 4 AS hires
    UNION ALL
    -- Live dynamic current period
    SELECT 
        '{rec_report_month}' AS period,
        COUNT(CASE WHEN approval_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS requisitions_opened,
        COUNT(CASE WHEN hire_date BETWEEN '{report_month_start}' AND '{report_month_end}' THEN 1 END) AS hires
    FROM (
        SELECT r.approval_date, o.hire_date
        FROM base_recruitment_requisitions_current r
        LEFT JOIN base_candidate_canonical c ON r.requisition_id = c.requisition_id
        LEFT JOIN base_onboarding_source_records o ON c.candidate_id = o.candidate_id
    );
    """)
    print("Created view 'mart_recruitment_trends'")

    # 18. Mart View: mart_recruitment_by_project
    conn.execute("""
    CREATE OR REPLACE VIEW mart_recruitment_by_project AS
    SELECT 
        project,
        COUNT(*) AS total_requisitions,
        COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS open_requisitions,
        COUNT(CASE WHEN status IN ('Closed', 'Filled') THEN 1 END) AS closed_requisitions,
        COUNT(CASE WHEN effective_target_hire_date < CURRENT_DATE AND status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS overdue_requisitions
    FROM base_recruitment_requisitions_current
    GROUP BY project;
    """)
    print("Created view 'mart_recruitment_by_project'")

    # 19. Mart View: mart_recruitment_by_department
    conn.execute("""
    CREATE OR REPLACE VIEW mart_recruitment_by_department AS
    SELECT 
        department,
        COUNT(*) AS total_requisitions,
        COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS open_requisitions,
        COUNT(CASE WHEN status IN ('Closed', 'Filled') THEN 1 END) AS closed_requisitions,
        COUNT(CASE WHEN effective_target_hire_date < CURRENT_DATE AND status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS overdue_requisitions
    FROM base_recruitment_requisitions_current
    GROUP BY department;
    """)
    print("Created view 'mart_recruitment_by_department'")

    # 20. Mart View: mart_recruitment_time_to_fill
    conn.execute("""
    CREATE OR REPLACE VIEW mart_recruitment_time_to_fill AS
    SELECT 
        r.department,
        r.project,
        COALESCE(ROUND(AVG(ob.hire_date - r.approval_date), 1), 0.0) AS average_time_to_fill,
        COUNT(ob.onboarding_record_id) AS hire_count
    FROM base_onboarding_source_records ob
    JOIN base_candidate_canonical c ON ob.candidate_id = c.candidate_id
    JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
    WHERE ob.hire_date IS NOT NULL AND r.approval_date IS NOT NULL
    GROUP BY r.department, r.project;
    """)
    print("Created view 'mart_recruitment_time_to_fill'")

    # 21. Mart View: mart_recruitment_source_effectiveness
    conn.execute("""
    CREATE OR REPLACE VIEW mart_recruitment_source_effectiveness AS
    SELECT 
        source,
        COUNT(*) AS candidate_count,
        COUNT(CASE WHEN pipeline_stage = 'Hired' THEN 1 END) AS hire_count,
        CASE 
            WHEN COUNT(*) = 0 THEN 0.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN pipeline_stage = 'Hired' THEN 1 END) / COUNT(*), 2)
        END AS conversion_pct
    FROM base_candidate_pipeline_current
    GROUP BY source;
    """)
    print("Created view 'mart_recruitment_source_effectiveness'")

    # 22. Mart View: mart_offer_acceptance
    conn.execute("""
    CREATE OR REPLACE VIEW mart_offer_acceptance AS
    SELECT 
        offer_status,
        COUNT(*) AS offer_count
    FROM base_offer_activity_current
    GROUP BY offer_status;
    """)
    print("Created view 'mart_offer_acceptance'")

    # 23. Mart View: mart_onboarding_status
    conn.execute("""
    CREATE OR REPLACE VIEW mart_onboarding_status AS
    SELECT 
        status AS onboarding_status,
        COUNT(*) AS hire_count
    FROM base_onboarding_current
    GROUP BY status;
    """)
    print("Created view 'mart_onboarding_status'")

    # 24. Mart View: mart_workforce_plan_vs_actual
    conn.execute("""
    CREATE OR REPLACE VIEW mart_workforce_plan_vs_actual AS
    SELECT 
        wp.project,
        wp.department,
        wp.planned_headcount,
        COALESCE(ahc.actual_count, 0) AS actual_headcount,
        CASE 
            WHEN wp.planned_headcount = 0 THEN 
                CASE WHEN COALESCE(ahc.actual_count, 0) = 0 THEN 100.0 ELSE 0.0 END
            ELSE ROUND(100.0 * COALESCE(ahc.actual_count, 0) / wp.planned_headcount, 2)
        END AS fulfillment_pct
    FROM base_workforce_plan_current wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM base_active_workforce
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department;
    """)
    print("Created view 'mart_workforce_plan_vs_actual'")

    # Automated reconciliation check
    print("Running warehouse reconciliation checks...")
    try:
        # Get active headcount
        hc_row = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()
        active_hc = hc_row[0] if hc_row else 0
        
        print(f"Active Headcount from KPIs view: {active_hc}")
        
        # Check distribution totals
        dist_rows = conn.execute("SELECT category, SUM(headcount) FROM mart_workforce_distribution GROUP BY category").fetchall()
        for cat, total in dist_rows:
            print(f"Distribution '{cat}' sum: {total}")
            if total != active_hc:
                raise ValueError(f"CRITICAL: Distribution '{cat}' sum ({total}) does not match Active Headcount ({active_hc})!")
                
        # Check contract expiry buckets total
        ce_row = conn.execute("SELECT expired + \"0_30\" + \"31_60\" + \"61_90\" + \"90_plus\" + missing_date FROM mart_workforce_contract_expiry").fetchone()
        ce_total = ce_row[0] if ce_row else 0
        print(f"Contract Expiry Buckets sum: {ce_total}")
        if ce_total != active_hc:
            raise ValueError(f"CRITICAL: Contract Expiry sum ({ce_total}) does not match Active Headcount ({active_hc})!")

        # Run payroll reconciliation checks
        print("Running payroll reconciliation checks...")
        
        # 1. SUM(gross_pay) equals total payroll cost KPI
        total_payroll_cost_kpi = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
        sum_gross_pay = conn.execute("SELECT SUM(gross_pay) FROM base_payroll_current").fetchone()[0]
        print(f"Total Payroll Cost KPI: {total_payroll_cost_kpi}, Sum Gross Pay: {sum_gross_pay}")
        if abs(total_payroll_cost_kpi - sum_gross_pay) > 0.01:
            raise ValueError(f"CRITICAL: Total Payroll Cost KPI ({total_payroll_cost_kpi}) does not match Sum Gross Pay ({sum_gross_pay})!")
            
        # 2. Gross components reconcile to gross pay
        # Verify that for all employees without a component mismatch exception, the components sum to gross pay.
        sum_reconciled_gross = conn.execute("""
            SELECT COALESCE(SUM(gross_pay) - SUM(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount), 0.0)
            FROM base_payroll_current
            WHERE employee_id NOT IN (
                SELECT employee_id FROM mart_payroll_exceptions WHERE issue_type = 'Payroll Component Mismatch'
            )
        """).fetchone()[0]
        print(f"Reconciled Gross Components Difference: {sum_reconciled_gross}")
        if abs(sum_reconciled_gross) > 0.01:
            raise ValueError(f"CRITICAL: Reconciled gross components differ from gross pay by {sum_reconciled_gross}!")
            
        # 3. Net payroll reconciles to gross minus deductions
        # Verify that for all employees without a net pay mismatch exception, net pay equals gross pay minus deductions.
        sum_reconciled_net = conn.execute("""
            SELECT COALESCE(SUM(net_pay) - SUM(gross_pay - deductions), 0.0)
            FROM base_payroll_current
            WHERE employee_id NOT IN (
                SELECT employee_id FROM mart_payroll_exceptions WHERE issue_type = 'Net Pay Mismatch'
            )
        """).fetchone()[0]
        print(f"Reconciled Net Payroll Difference: {sum_reconciled_net}")
        if abs(sum_reconciled_net) > 0.01:
            raise ValueError(f"CRITICAL: Reconciled net payroll differs from gross minus deductions by {sum_reconciled_net}!")
            
        # 4. Project payroll totals reconcile to total payroll cost
        sum_project_cost = conn.execute("SELECT SUM(total_payroll_cost) FROM mart_payroll_by_project").fetchone()[0]
        print(f"Sum Project Payroll Cost: {sum_project_cost}")
        if abs(total_payroll_cost_kpi - sum_project_cost) > 0.01:
            raise ValueError(f"CRITICAL: Project Payroll sum ({sum_project_cost}) does not match Total Payroll Cost ({total_payroll_cost_kpi})!")
            
        # 5. Department payroll totals reconcile to total payroll cost
        sum_dept_cost = conn.execute("SELECT SUM(total_payroll_cost) FROM mart_payroll_by_department").fetchone()[0]
        print(f"Sum Department Payroll Cost: {sum_dept_cost}")
        if abs(total_payroll_cost_kpi - sum_dept_cost) > 0.01:
            raise ValueError(f"CRITICAL: Department Payroll sum ({sum_dept_cost}) does not match Total Payroll Cost ({total_payroll_cost_kpi})!")
            
        # 6. Employees paid KPI reconciles to distinct payroll employee count
        employees_paid_kpi = conn.execute("SELECT employees_paid FROM mart_payroll_kpis").fetchone()[0]
        distinct_paid_employees = conn.execute("SELECT COUNT(DISTINCT employee_id) FROM base_payroll_current").fetchone()[0]
        print(f"Employees Paid KPI: {employees_paid_kpi}, Distinct Paid Employees: {distinct_paid_employees}")
        if employees_paid_kpi != distinct_paid_employees:
            raise ValueError(f"CRITICAL: Employees Paid KPI ({employees_paid_kpi}) does not match Distinct Paid Employees ({distinct_paid_employees})!")
            
        # 7. Payroll exception count reconciles to mart_payroll_exceptions
        exception_count_kpi = conn.execute("SELECT payroll_exception_count FROM mart_payroll_kpis").fetchone()[0]
        actual_exceptions = conn.execute("SELECT COUNT(*) FROM mart_payroll_exceptions").fetchone()[0]
        print(f"Exception Count KPI: {exception_count_kpi}, Actual Exceptions: {actual_exceptions}")
        if exception_count_kpi != actual_exceptions:
            raise ValueError(f"CRITICAL: Exception Count KPI ({exception_count_kpi}) does not match Actual Exceptions ({actual_exceptions})!")
            
        # Run attendance reconciliation checks
        print("Running attendance reconciliation checks...")
        
        # 1. Expected workdays reconcile to generated employee-calendar rows
        expected_workdays_count = conn.execute("SELECT COUNT(*) FROM base_expected_attendance").fetchone()[0]
        calendar_rows_count = conn.execute(f"""
            SELECT COUNT(*) 
            FROM (
                SELECT CAST(range AS DATE) AS d 
                FROM range(
                    CAST(DATE '{start_date_str}' AS TIMESTAMP),
                    CAST(DATE '{end_date_str}' + INTERVAL 1 DAY AS TIMESTAMP),
                    INTERVAL 1 DAY
                )
            ) c
            CROSS JOIN base_employees_deduplicated e
            WHERE e.status = 'Active'
              AND c.d >= e.joining_date 
              AND (e.termination_date IS NULL OR c.d <= e.termination_date)
              AND dayname(c.d) NOT IN ('Friday')
        """).fetchone()[0]
        print(f"Expected Workdays Count: {expected_workdays_count}, Calendar Rows Count: {calendar_rows_count}")
        if expected_workdays_count != calendar_rows_count:
            raise ValueError(f"CRITICAL: Expected workdays count ({expected_workdays_count}) does not match calendar rows count ({calendar_rows_count})!")

        # 2. Absence days reconcile to expected workdays without valid attendance/leave
        absence_days_kpi = conn.execute("SELECT absence_days FROM mart_attendance_kpis").fetchone()[0]
        absence_days_calc = conn.execute("SELECT COUNT(*) FROM base_expected_attendance WHERE attendance_date IS NULL OR absence_days = 1.0").fetchone()[0]
        print(f"Absence Days KPI: {absence_days_kpi}, Calculated: {absence_days_calc}")
        if abs(absence_days_kpi - absence_days_calc) > 0.01:
            raise ValueError(f"CRITICAL: Absence Days KPI ({absence_days_kpi}) does not match calculated ({absence_days_calc})!")

        # 3. Late minutes reconcile to calculated late minutes
        late_minutes_kpi = conn.execute("SELECT late_minutes FROM mart_attendance_kpis").fetchone()[0]
        late_minutes_calc = conn.execute("SELECT SUM(calculated_late_minutes) FROM base_attendance_current").fetchone()[0]
        print(f"Late Minutes KPI: {late_minutes_kpi}, Calculated: {late_minutes_calc}")
        if abs(late_minutes_kpi - late_minutes_calc) > 0.01:
            raise ValueError(f"CRITICAL: Late minutes KPI ({late_minutes_kpi}) does not match calculated ({late_minutes_calc})!")

        # 4. Net late minutes equal calculated late minutes minus excused late minutes, never below zero
        net_late_mismatch = conn.execute("""
            SELECT COUNT(*) 
            FROM base_attendance_current 
            WHERE calculated_net_late_minutes != GREATEST(calculated_late_minutes - COALESCE(excused_late_minutes, 0), 0)
        """).fetchone()[0]
        print(f"Net late minutes mismatch count: {net_late_mismatch}")
        if net_late_mismatch > 0:
            raise ValueError("CRITICAL: Calculated net late minutes logic check failed!")

        # 5. Missing punch count reconciles to missing punch exception records
        missing_punch_kpi = conn.execute("SELECT missing_punch_count FROM mart_attendance_kpis").fetchone()[0]
        missing_punch_calc = conn.execute("""
            SELECT COUNT(*) 
            FROM mart_attendance_exceptions 
            WHERE issue_type IN ('Missing Check-in', 'Missing Check-out')
        """).fetchone()[0]
        print(f"Missing Punch KPI: {missing_punch_kpi}, Calculated Exceptions: {missing_punch_calc}")
        if missing_punch_kpi != missing_punch_calc:
            raise ValueError(f"CRITICAL: Missing Punch KPI ({missing_punch_kpi}) does not match exceptions ({missing_punch_calc})!")

        # 6. Approved overtime hours reconcile to attendance overtime records
        ot_hours_kpi = conn.execute("SELECT overtime_hours FROM mart_attendance_kpis").fetchone()[0]
        ot_hours_calc = conn.execute("SELECT SUM(attendance_ot_hours) FROM base_attendance_payroll_overtime").fetchone()[0]
        print(f"Overtime Hours KPI: {ot_hours_kpi}, Calculated: {ot_hours_calc}")
        if abs(ot_hours_kpi - ot_hours_calc) > 0.01:
            raise ValueError(f"CRITICAL: Overtime Hours KPI ({ot_hours_kpi}) does not match calculated ({ot_hours_calc})!")

        # 7. Payroll overtime cost reconciles to payroll overtime amount by employee and period
        ot_cost_kpi = conn.execute("SELECT overtime_cost FROM mart_attendance_kpis").fetchone()[0]
        ot_cost_calc = conn.execute("SELECT SUM(payroll_ot_cost) FROM base_attendance_payroll_overtime").fetchone()[0]
        print(f"Overtime Cost KPI: {ot_cost_kpi}, Calculated: {ot_cost_calc}")
        if abs(ot_cost_kpi - ot_cost_calc) > 0.01:
            raise ValueError(f"CRITICAL: Overtime Cost KPI ({ot_cost_kpi}) does not match calculated ({ot_cost_calc})!")

        # 8. Attendance exception count reconciles to mart_attendance_exceptions
        att_exceptions_kpi = conn.execute("SELECT attendance_exception_count FROM mart_attendance_kpis").fetchone()[0]
        att_exceptions_calc = conn.execute("SELECT COUNT(*) FROM mart_attendance_exceptions").fetchone()[0]
        print(f"Attendance Exception Count KPI: {att_exceptions_kpi}, Calculated: {att_exceptions_calc}")
        if att_exceptions_kpi != att_exceptions_calc:
            raise ValueError(f"CRITICAL: Exception Count KPI ({att_exceptions_kpi}) does not match calculated exceptions ({att_exceptions_calc})!")

        # -------------------------------------------------------------
        # Milestone 2D: Saudization & Compliance Reconciliation Checks
        # -------------------------------------------------------------
        print("Running compliance reconciliation checks...")
        
        # 1. Saudi + Non-Saudi + Missing Nationality reconcile to active headcount
        kpi_saudi = conn.execute("SELECT saudi_headcount FROM mart_compliance_kpis").fetchone()[0]
        kpi_non_saudi = conn.execute("SELECT non_saudi_headcount FROM mart_compliance_kpis").fetchone()[0]
        kpi_missing_nat = conn.execute("SELECT employees_missing_nationality FROM mart_compliance_kpis").fetchone()[0]
        print(f"Saudi HC: {kpi_saudi}, Non-Saudi HC: {kpi_non_saudi}, Missing Nationality: {kpi_missing_nat}, Active Headcount: {active_hc}")
        if kpi_saudi + kpi_non_saudi + kpi_missing_nat != active_hc:
            raise ValueError(f"CRITICAL: Active Headcount breakdown ({kpi_saudi} + {kpi_non_saudi} + {kpi_missing_nat} = {kpi_saudi + kpi_non_saudi + kpi_missing_nat}) does not reconcile to Active Headcount ({active_hc})!")

        # 2. Saudization % reconciles to Saudi / (Saudi + Non-Saudi) population
        kpi_saudization = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
        valid_nat_hc = kpi_saudi + kpi_non_saudi
        expected_pct = round(100.0 * kpi_saudi / valid_nat_hc, 2) if valid_nat_hc > 0 else 0.0
        print(f"Saudization KPI %: {kpi_saudization}, Expected: {expected_pct}%")
        if abs(kpi_saudization - expected_pct) > 0.01:
            raise ValueError(f"CRITICAL: Saudization % KPI ({kpi_saudization}) does not match expected ({expected_pct})!")

        # 3. Project Saudization totals reconcile to active workforce population
        sum_project_hc = conn.execute("SELECT SUM(saudi_headcount + non_saudi_headcount + employees_missing_nationality) FROM mart_saudization_by_project").fetchone()[0]
        print(f"Sum Project Headcount: {sum_project_hc}, Active Headcount: {active_hc}")
        if sum_project_hc != active_hc:
            raise ValueError(f"CRITICAL: Project headcount sum ({sum_project_hc}) does not match Active Headcount ({active_hc})!")

        # 4. Department Saudization totals reconcile to active workforce population
        sum_dept_hc = conn.execute("SELECT SUM(saudi_headcount + non_saudi_headcount + employees_missing_nationality) FROM mart_saudization_by_department").fetchone()[0]
        print(f"Sum Department Headcount: {sum_dept_hc}, Active Headcount: {active_hc}")
        if sum_dept_hc != active_hc:
            raise ValueError(f"CRITICAL: Department headcount sum ({sum_dept_hc}) does not match Active Headcount ({active_hc})!")

        # 5. Iqama expiry buckets reconcile to active non-Saudi population
        sum_iqama_buckets = conn.execute("SELECT SUM(iqama_count) FROM mart_document_expiry").fetchone()[0]
        print(f"Sum Iqama Buckets: {sum_iqama_buckets}, Non-Saudi Headcount: {kpi_non_saudi}")
        if sum_iqama_buckets != kpi_non_saudi:
            raise ValueError(f"CRITICAL: Iqama expiry buckets sum ({sum_iqama_buckets}) does not match Non-Saudi Headcount ({kpi_non_saudi})!")

        # 6. Work permit expiry buckets reconcile to active non-Saudi population
        sum_wp_buckets = conn.execute("SELECT SUM(work_permit_count) FROM mart_document_expiry").fetchone()[0]
        print(f"Sum Work Permit Buckets: {sum_wp_buckets}, Non-Saudi Headcount: {kpi_non_saudi}")
        if sum_wp_buckets != kpi_non_saudi:
            raise ValueError(f"CRITICAL: Work permit expiry buckets sum ({sum_wp_buckets}) does not match Non-Saudi Headcount ({kpi_non_saudi})!")

        # 7. GOSI status distribution reconciles to active workforce population
        gosi_dist_sum = conn.execute("SELECT SUM(employee_count) FROM mart_gosi_status").fetchone()[0]
        print(f"Sum GOSI status distribution: {gosi_dist_sum}, Active Headcount: {active_hc}")
        if gosi_dist_sum != active_hc:
            raise ValueError(f"CRITICAL: GOSI distribution sum ({gosi_dist_sum}) does not match Active Headcount ({active_hc})!")

        # 8. WPS status distribution reconciles to active workforce population
        wps_dist_sum = conn.execute("SELECT SUM(headcount) FROM mart_wps_status").fetchone()[0]
        print(f"Sum WPS status distribution: {wps_dist_sum}, Active Headcount: {active_hc}")
        if wps_dist_sum != active_hc:
            raise ValueError(f"CRITICAL: WPS distribution sum ({wps_dist_sum}) does not match Active Headcount ({active_hc})!")

        # 9. Compliance exception count reconciles to mart_compliance_exceptions
        kpi_exc_count = conn.execute("SELECT compliance_exception_count FROM mart_compliance_kpis").fetchone()[0]
        actual_exc_count = conn.execute("SELECT COUNT(*) FROM mart_compliance_exceptions").fetchone()[0]
        print(f"Compliance Exception Count KPI: {kpi_exc_count}, Exceptions Table count: {actual_exc_count}")
        if kpi_exc_count != actual_exc_count:
            raise ValueError(f"CRITICAL: Compliance Exception Count KPI ({kpi_exc_count}) does not match exceptions table count ({actual_exc_count})!")

        # -------------------------------------------------------------
        # Milestone 2E: Employee Relations & SLA Reconciliation Checks
        # -------------------------------------------------------------
        print("Running Employee Relations & SLA reconciliation checks...")
        er_pop_count = conn.execute("SELECT COUNT(*) FROM base_er_case_population").fetchone()[0]
        kpis_row = conn.execute("""
            SELECT 
                total_open_er_cases, 
                new_cases_this_month, 
                closed_cases_this_month, 
                overdue_cases, 
                sla_compliance_pct, 
                er_exception_count 
            FROM mart_er_kpis
        """).fetchone()
        
        kpi_open = kpis_row[0]
        kpi_new = kpis_row[1]
        kpi_closed = kpis_row[2]
        kpi_overdue = kpis_row[3]
        kpi_sla_pct = kpis_row[4]
        kpi_er_exc = kpis_row[5]

        # 1. Total Open ER Cases
        calc_open = conn.execute("SELECT COUNT(*) FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending')").fetchone()[0]
        print(f"ER Open Cases KPI: {kpi_open}, Calculated: {calc_open}")
        if kpi_open != calc_open:
            raise ValueError(f"CRITICAL: Open cases KPI ({kpi_open}) does not match calculated ({calc_open})!")

        # 2. Closed Cases This Month
        calc_closed = conn.execute(f"SELECT COUNT(*) FROM base_er_case_population WHERE closed_date BETWEEN '{report_month_start}' AND '{report_month_end}'").fetchone()[0]
        print(f"ER Closed Cases KPI: {kpi_closed}, Calculated: {calc_closed}")
        if kpi_closed != calc_closed:
            raise ValueError(f"CRITICAL: Closed cases KPI ({kpi_closed}) does not match calculated ({calc_closed})!")

        # 3. New Cases This Month
        calc_new = conn.execute(f"SELECT COUNT(*) FROM base_er_case_population WHERE created_date BETWEEN '{report_month_start}' AND '{report_month_end}'").fetchone()[0]
        print(f"ER New Cases KPI: {kpi_new}, Calculated: {calc_new}")
        if kpi_new != calc_new:
            raise ValueError(f"CRITICAL: New cases KPI ({kpi_new}) does not match calculated ({calc_new})!")

        # 4. Case Type Distribution Sum
        type_sum = conn.execute("SELECT SUM(case_count) FROM mart_er_case_type_distribution").fetchone()[0] or 0
        print(f"Sum Case Type Distribution: {type_sum}, Total ER Population: {er_pop_count}")
        if type_sum != er_pop_count:
            raise ValueError(f"CRITICAL: Case type distribution sum ({type_sum}) does not match total ER population ({er_pop_count})!")

        # 5. Case Status Distribution Sum
        status_sum = conn.execute("SELECT SUM(case_count) FROM mart_er_case_status_distribution").fetchone()[0] or 0
        print(f"Sum Case Status Distribution: {status_sum}, Total ER Population: {er_pop_count}")
        if status_sum != er_pop_count:
            raise ValueError(f"CRITICAL: Case status distribution sum ({status_sum}) does not match total ER population ({er_pop_count})!")

        # 6. Project Case Totals Sum
        proj_sum = conn.execute("SELECT SUM(total_cases) FROM mart_er_cases_by_project").fetchone()[0] or 0
        print(f"Sum Project Cases: {proj_sum}, Total ER Population: {er_pop_count}")
        if proj_sum != er_pop_count:
            raise ValueError(f"CRITICAL: Project cases sum ({proj_sum}) does not match total ER population ({er_pop_count})!")

        # 7. Department Case Totals Sum
        dept_sum = conn.execute("SELECT SUM(total_cases) FROM mart_er_cases_by_department").fetchone()[0] or 0
        print(f"Sum Department Cases: {dept_sum}, Total ER Population: {er_pop_count}")
        if dept_sum != er_pop_count:
            raise ValueError(f"CRITICAL: Department cases sum ({dept_sum}) does not match total ER population ({er_pop_count})!")

        # 8. SLA Compliance % Check
        sla_eligible = conn.execute("SELECT COUNT(*) FROM base_er_case_population WHERE sla_status IN ('Compliant', 'Breached')").fetchone()[0]
        sla_compliant = conn.execute("SELECT COUNT(*) FROM base_er_case_population WHERE sla_status = 'Compliant'").fetchone()[0]
        expected_sla_pct = round(100.0 * sla_compliant / sla_eligible, 2) if sla_eligible > 0 else 100.0
        print(f"ER SLA Compliance % KPI: {kpi_sla_pct}, Expected: {expected_sla_pct}%")
        if abs(kpi_sla_pct - expected_sla_pct) > 0.01:
            raise ValueError(f"CRITICAL: ER SLA Compliance KPI ({kpi_sla_pct}) does not match expected ({expected_sla_pct})!")

        # 9. Overdue Cases Check (using effective_target_due_date)
        calc_overdue = conn.execute(f"SELECT COUNT(*) FROM base_er_case_population WHERE case_status IN ('Open', 'In Progress', 'Pending') AND '{report_anchor_date}' > effective_target_due_date").fetchone()[0]
        print(f"ER Overdue Cases KPI: {kpi_overdue}, Calculated: {calc_overdue}")
        if kpi_overdue != calc_overdue:
            raise ValueError(f"CRITICAL: Overdue cases KPI ({kpi_overdue}) does not match calculated ({calc_overdue})!")

        # 10. ER Exception Count Check
        actual_er_exc = conn.execute("SELECT COUNT(*) FROM mart_er_exceptions").fetchone()[0]
        print(f"ER Exception Count KPI: {kpi_er_exc}, Calculated: {actual_er_exc}")
        if kpi_er_exc != actual_er_exc:
            raise ValueError(f"CRITICAL: ER Exception Count KPI ({kpi_er_exc}) does not match calculated exceptions ({actual_er_exc})!")

        # 11. Aging Bucket Reconciliation
        calc_aging_sum = conn.execute("SELECT SUM(case_count) FROM mart_er_aging_buckets").fetchone()[0] or 0
        print(f"Sum ER Aging Buckets: {calc_aging_sum}, Open Cases KPI: {kpi_open}")
        if calc_aging_sum != kpi_open:
            raise ValueError(f"CRITICAL: Aging buckets sum ({calc_aging_sum}) does not match Open Cases KPI ({kpi_open})!")

        # -------------------------------------------------------------
        # Milestone 2F: Recruitment & Workforce Planning Checks
        # -------------------------------------------------------------
        print("Running Recruitment & Workforce Planning reconciliation checks...")
        
        req_pop_count = conn.execute("SELECT COUNT(*) FROM base_recruitment_requisitions_current").fetchone()[0]
        rec_kpis = conn.execute("""
            SELECT 
                open_requisitions, approved_vacancies, candidates_in_pipeline, 
                interviews_scheduled, offers_extended, offer_acceptance_pct, 
                hires_this_month, average_time_to_fill, overdue_requisitions, 
                workforce_plan_fulfillment_pct, recruitment_exception_count
            FROM mart_recruitment_kpis
        """).fetchone()

        kpi_open_reqs = rec_kpis[0]
        kpi_app_vac = rec_kpis[1]
        kpi_pipeline = rec_kpis[2]
        kpi_interviews = rec_kpis[3]
        kpi_offers = rec_kpis[4]
        kpi_offer_acc = rec_kpis[5]
        kpi_hires = rec_kpis[6]
        kpi_ttf = rec_kpis[7]
        kpi_overdue_reqs = rec_kpis[8]
        kpi_plan_ful = rec_kpis[9]
        kpi_rec_exc = rec_kpis[10]

        # 1. Open Requisitions
        calc_open_reqs = conn.execute("SELECT COUNT(*) FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold')").fetchone()[0]
        print(f"Open Requisitions KPI: {kpi_open_reqs}, Calculated: {calc_open_reqs}")
        if kpi_open_reqs != calc_open_reqs:
            raise ValueError(f"CRITICAL: Open Requisitions KPI ({kpi_open_reqs}) does not match calculated ({calc_open_reqs})!")

        # 2. Approved Vacancies quantity sum
        calc_app_vac = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM base_vacancy_population").fetchone()[0]
        print(f"Approved Vacancies KPI: {kpi_app_vac}, Calculated: {calc_app_vac}")
        if kpi_app_vac != calc_app_vac:
            raise ValueError(f"CRITICAL: Approved Vacancies KPI ({kpi_app_vac}) does not match calculated ({calc_app_vac})!")

        # 3. Candidates in Pipeline
        calc_pipeline = conn.execute("SELECT COUNT(*) FROM base_candidate_pipeline_current").fetchone()[0]
        print(f"Candidates KPI: {kpi_pipeline}, Calculated: {calc_pipeline}")
        if kpi_pipeline != calc_pipeline:
            raise ValueError(f"CRITICAL: Candidates KPI ({kpi_pipeline}) does not match calculated ({calc_pipeline})!")

        # 4. Interviews Scheduled
        calc_interviews = conn.execute(f"SELECT COUNT(*) FROM base_interview_activity_current").fetchone()[0]
        print(f"Interviews KPI: {kpi_interviews}, Calculated: {calc_interviews}")
        if kpi_interviews != calc_interviews:
            raise ValueError(f"CRITICAL: Interviews KPI ({kpi_interviews}) does not match calculated ({calc_interviews})!")

        # 5. Offers Extended
        calc_offers = conn.execute(f"SELECT COUNT(*) FROM base_offer_activity_current").fetchone()[0]
        print(f"Offers KPI: {kpi_offers}, Calculated: {calc_offers}")
        if kpi_offers != calc_offers:
            raise ValueError(f"CRITICAL: Offers KPI ({kpi_offers}) does not match calculated ({calc_offers})!")

        # 6. Offer Acceptance %
        off_accepted = conn.execute("SELECT COUNT(*) FROM base_offer_activity_current WHERE offer_status = 'Accepted'").fetchone()[0]
        off_decided = conn.execute("SELECT COUNT(*) FROM base_offer_activity_current WHERE offer_status IN ('Accepted', 'Rejected', 'Declined')").fetchone()[0]
        expected_offer_acc = round(100.0 * off_accepted / off_decided, 2) if off_decided > 0 else 100.0
        print(f"Offer Acceptance % KPI: {kpi_offer_acc}, Expected: {expected_offer_acc}%")
        if abs(kpi_offer_acc - expected_offer_acc) > 0.01:
            raise ValueError(f"CRITICAL: Offer Acceptance KPI ({kpi_offer_acc}) does not match expected ({expected_offer_acc})!")

        # 7. Hires This Month
        calc_hires = conn.execute(f"SELECT COUNT(*) FROM base_onboarding_current").fetchone()[0]
        print(f"Hires KPI: {kpi_hires}, Calculated: {calc_hires}")
        if kpi_hires != calc_hires:
            raise ValueError(f"CRITICAL: Hires KPI ({kpi_hires}) does not match calculated ({calc_hires})!")

        # 8. Average Time to Fill
        calc_ttf = conn.execute(f"""
            SELECT COALESCE(ROUND(AVG(ob.hire_date - r.approval_date), 1), 0.0)
            FROM base_onboarding_source_records ob
            JOIN base_candidate_canonical c ON ob.candidate_id = c.candidate_id
            JOIN base_recruitment_requisitions_current r ON c.requisition_id = r.requisition_id
            WHERE ob.hire_date IS NOT NULL AND r.approval_date IS NOT NULL
        """).fetchone()[0]
        print(f"Time to Fill KPI: {kpi_ttf}, Calculated: {calc_ttf}")
        if abs(kpi_ttf - calc_ttf) > 0.01:
            raise ValueError(f"CRITICAL: Time to Fill KPI ({kpi_ttf}) does not match calculated ({calc_ttf})!")

        # 9. Overdue Requisitions
        calc_overdue_reqs = conn.execute(f"SELECT COUNT(*) FROM base_recruitment_requisitions_current WHERE status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND '{report_anchor_date}' > effective_target_hire_date").fetchone()[0]
        print(f"Overdue Requisitions KPI: {kpi_overdue_reqs}, Calculated: {calc_overdue_reqs}")
        if kpi_overdue_reqs != calc_overdue_reqs:
            raise ValueError(f"CRITICAL: Overdue Requisitions KPI ({kpi_overdue_reqs}) does not match calculated ({calc_overdue_reqs})!")

        # 10. Workforce Plan Fulfillment %
        calc_plan_planned = conn.execute("SELECT SUM(planned_headcount) FROM base_workforce_plan_current").fetchone()[0] or 0
        calc_plan_actual = conn.execute("""
            SELECT COUNT(aw.employee_id)
            FROM base_workforce_plan_current wp
            LEFT JOIN base_active_workforce aw ON wp.project = aw.project AND wp.department = aw.department
        """).fetchone()[0]
        if calc_plan_planned == 0:
            expected_ful = 100.0 if calc_plan_actual == 0 else 0.0
        else:
            expected_ful = round(100.0 * calc_plan_actual / calc_plan_planned, 2)
        print(f"Workforce Plan Fulfillment % KPI: {kpi_plan_ful}, Expected: {expected_ful}%")
        if abs(kpi_plan_ful - expected_ful) > 0.01:
            raise ValueError(f"CRITICAL: Workforce Plan Fulfillment KPI ({kpi_plan_ful}) does not match expected ({expected_ful})!")

        # 11. Project Requisition Totals
        sum_proj_reqs = conn.execute("SELECT SUM(total_requisitions) FROM mart_recruitment_by_project").fetchone()[0] or 0
        print(f"Sum Project Requisitions: {sum_proj_reqs}, Total Requisitions: {req_pop_count}")
        if sum_proj_reqs != req_pop_count:
            raise ValueError(f"CRITICAL: Project requisitions sum ({sum_proj_reqs}) does not match total requisitions ({req_pop_count})!")

        # 12. Department Requisition Totals
        sum_dept_reqs = conn.execute("SELECT SUM(total_requisitions) FROM mart_recruitment_by_department").fetchone()[0] or 0
        print(f"Sum Department Requisitions: {sum_dept_reqs}, Total Requisitions: {req_pop_count}")
        if sum_dept_reqs != req_pop_count:
            raise ValueError(f"CRITICAL: Department requisitions sum ({sum_dept_reqs}) does not match total requisitions ({req_pop_count})!")

        # 13. Recruitment Exception Count
        actual_rec_exc = conn.execute("SELECT COUNT(*) FROM mart_recruitment_exceptions").fetchone()[0]
        print(f"Recruitment Exception Count KPI: {kpi_rec_exc}, Calculated: {actual_rec_exc}")
        if kpi_rec_exc != actual_rec_exc:
            raise ValueError(f"CRITICAL: Exception Count KPI ({kpi_rec_exc}) does not match calculated exceptions ({actual_rec_exc})!")

        print("Reconciliation checks PASSED.")
    except Exception as e:
        print(f"Reconciliation check FAILED: {str(e)}")
        # Raise error to fail the build/pipeline!
        raise e

    # -----------------------------------------------------------------
    # Milestone 2G: Talent, Performance, Learning & Succession Dashboard
    # -----------------------------------------------------------------
    talent_rules = rules.get("talent_rules", {})
    talent_default_report_month = talent_rules.get("default_report_month", "2026-06")
    min_rating = talent_rules.get("min_rating_value", 1.0)
    max_rating = talent_rules.get("max_rating_value", 5.0)
    critical_job_titles = talent_rules.get("critical_job_titles", [])
    critical_titles_sql = ", ".join([f"'{t}'" for t in critical_job_titles])

    # Resolve report month using the 5-tier priority:
    # 1. configured month in business_rules, 2. max review period, 3. max learning enrollment date,
    # 4. max talent review, 5. default
    talent_configured_month = talent_rules.get("configured_report_month", None)
    talent_report_month = None

    if talent_configured_month:
        talent_report_month = talent_configured_month
    if not talent_report_month:
        try:
            row = conn.execute("SELECT MAX(review_period) FROM performance_reviews WHERE review_period IS NOT NULL").fetchone()
            if row and row[0]:
                talent_report_month = str(row[0])[:7]
        except Exception:
            pass
    if not talent_report_month:
        try:
            row = conn.execute("SELECT MAX(completion_date) FROM learning_enrollments WHERE completion_date IS NOT NULL").fetchone()
            if row and row[0]:
                talent_report_month = str(row[0])[:7]
        except Exception:
            pass
    if not talent_report_month:
        try:
            row = conn.execute("SELECT MAX(review_id) FROM talent_reviews WHERE review_id IS NOT NULL").fetchone()
            # No date in talent_reviews; use default
        except Exception:
            pass
    if not talent_report_month:
        talent_report_month = talent_default_report_month

    print(f"Using Talent report month: {talent_report_month}")
    tal_month_start = f"{talent_report_month}-01"
    tal_month_end_date = conn.execute(f"SELECT last_day(CAST('{tal_month_start}' AS DATE))").fetchone()[0]
    tal_month_end = str(tal_month_end_date)
    tal_anchor_date = tal_month_end

    # ----- Source-level views with deterministic stable row-level keys -----
    conn.execute("""
    CREATE OR REPLACE VIEW base_performance_review_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY review_id, employee_id, completed_date, rating) AS performance_review_record_id,
        review_id, employee_id, reviewer_id, review_period, rating, status, completed_date
    FROM performance_reviews;
    """)
    print("Created view 'base_performance_review_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_performance_goal_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY goal_id, employee_id, due_date) AS performance_goal_record_id,
        goal_id, employee_id, title, status, due_date, completed_date
    FROM performance_goals;
    """)
    print("Created view 'base_performance_goal_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_competency_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY assessment_id, employee_id, competency_name, assessed_date) AS competency_assessment_record_id,
        assessment_id, employee_id, competency_name, required_score, actual_score, assessed_date
    FROM competency_assessments;
    """)
    print("Created view 'base_competency_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_learning_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY enrollment_id, employee_id, course_id, enrollment_date) AS learning_enrollment_record_id,
        enrollment_id, employee_id, course_id, status, enrollment_date, completion_date
    FROM learning_enrollments;
    """)
    print("Created view 'base_learning_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_succession_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY plan_id, critical_role_id, successor_employee_id) AS succession_plan_record_id,
        plan_id, critical_role_id, role_title, current_employee_id, successor_employee_id, readiness, flight_risk, is_critical
    FROM succession_plans;
    """)
    print("Created view 'base_succession_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_talent_review_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY review_id, employee_id, performance_rating) AS talent_review_record_id,
        review_id, employee_id, performance_rating, potential_rating, flight_risk, retention_risk
    FROM talent_reviews;
    """)
    print("Created view 'base_talent_review_source_records'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_employee_skill_source_records AS
    SELECT
        ROW_NUMBER() OVER (ORDER BY skill_id, employee_id, skill_name) AS employee_skill_record_id,
        skill_id, employee_id, skill_name, proficiency
    FROM employee_skills;
    """)
    print("Created view 'base_employee_skill_source_records'")

    # ----- Base population views -----
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_talent_employee_population AS
    SELECT employee_id, employee_name, department, project, job_title, status
    FROM base_active_workforce
    WHERE employee_id IS NOT NULL AND TRIM(employee_id) != '';
    """)
    print("Created view 'base_talent_employee_population'")

    # Canonical latest completed review per employee (deduplicated to prevent inflation)
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_performance_reviews_current AS
    WITH ranked AS (
        SELECT s.*,
            CASE
                WHEN s.rating >= 4.5 THEN 'Outstanding'
                WHEN s.rating >= 3.5 THEN 'Exceeds Expectations'
                WHEN s.rating >= 2.5 THEN 'Meets Expectations'
                WHEN s.rating >= 1.5 THEN 'Needs Improvement'
                WHEN s.rating IS NOT NULL THEN 'Unsatisfactory'
                ELSE NULL
            END AS performance_category,
            ROW_NUMBER() OVER (PARTITION BY s.employee_id ORDER BY s.completed_date DESC, s.performance_review_record_id DESC) AS rn
        FROM base_performance_review_source_records s
        WHERE s.status = 'Completed'
          AND s.review_period = '{talent_report_month}'
          AND s.employee_id IN (SELECT employee_id FROM base_talent_employee_population)
          AND s.rating IS NOT NULL
          AND s.rating BETWEEN {min_rating} AND {max_rating}
    )
    SELECT * FROM ranked WHERE rn = 1;
    """)
    print("Created view 'base_performance_reviews_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_performance_goals_current AS
    SELECT g.*
    FROM base_performance_goal_source_records g
    WHERE g.employee_id IN (SELECT employee_id FROM base_talent_employee_population)
      AND g.status IS NOT NULL;
    """)
    print("Created view 'base_performance_goals_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_competency_assessments_current AS
    SELECT c.*
    FROM base_competency_source_records c
    WHERE c.employee_id IN (SELECT employee_id FROM base_talent_employee_population)
      AND c.required_score BETWEEN {min_rating} AND {max_rating}
      AND c.actual_score BETWEEN {min_rating} AND {max_rating};
    """)
    print("Created view 'base_competency_assessments_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_learning_enrollments_current AS
    SELECT l.*
    FROM base_learning_source_records l
    WHERE l.employee_id IN (SELECT employee_id FROM base_talent_employee_population)
      AND l.enrollment_date <= DATE '{tal_month_end}';
    """)
    print("Created view 'base_learning_enrollments_current'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_training_catalog_current AS
    SELECT * FROM training_catalog;
    """)
    print("Created view 'base_training_catalog_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_succession_plans_current AS
    SELECT s.*
    FROM base_succession_source_records s
    WHERE (s.is_critical = TRUE OR s.role_title IN ({critical_titles_sql if critical_titles_sql else "''"}));
    """)
    print("Created view 'base_succession_plans_current'")

    # Canonical latest talent review per employee
    conn.execute(f"""
    CREATE OR REPLACE VIEW base_talent_reviews_current AS
    WITH ranked AS (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY talent_review_record_id DESC) AS rn
        FROM base_talent_review_source_records
        WHERE employee_id IN (SELECT employee_id FROM base_talent_employee_population)
    )
    SELECT * FROM ranked WHERE rn = 1;
    """)
    print("Created view 'base_talent_reviews_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_employee_skills_current AS
    SELECT s.*
    FROM base_employee_skill_source_records s
    WHERE s.employee_id IN (SELECT employee_id FROM base_talent_employee_population);
    """)
    print("Created view 'base_employee_skills_current'")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_career_paths_current AS
    SELECT * FROM career_paths
    WHERE employee_id IN (SELECT employee_id FROM base_talent_employee_population);
    """)
    print("Created view 'base_career_paths_current'")

    # ----- Analytical Mart Views -----

    # mart_talent_exceptions (24 checks)
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_talent_exceptions AS
    -- 1. Active employee missing performance review
    SELECT e.employee_id AS record_id_str, 'Missing Performance Review' AS issue_type,
        'Active employee ' || e.employee_id || ' has no completed review for ' || '{talent_report_month}' AS description,
        'Warning' AS severity, 'Assign and complete a performance review' AS recommended_action
    FROM base_talent_employee_population e
    WHERE e.employee_id NOT IN (SELECT DISTINCT employee_id FROM base_performance_reviews_current)
    UNION ALL
    -- 2. Performance review linked to unknown employee
    SELECT s.employee_id AS record_id_str, 'Review Linked to Unknown Employee' AS issue_type,
        'Review ID ' || s.review_id || ' links to employee_id ' || s.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on review record' AS recommended_action
    FROM base_performance_review_source_records s
    WHERE s.employee_id NOT IN (SELECT employee_id FROM base_talent_employee_population)
    UNION ALL
    -- 3. Duplicate performance review ID
    SELECT s.review_id AS record_id_str, 'Duplicate Performance Review ID' AS issue_type,
        'Review ID ' || s.review_id || ' appears more than once in source records' AS description,
        'Critical' AS severity, 'Deduplicate performance review records' AS recommended_action
    FROM base_performance_review_source_records s
    WHERE s.review_id IN (SELECT review_id FROM base_performance_review_source_records GROUP BY 1 HAVING COUNT(*) > 1)
    UNION ALL
    -- 4. Review completed without rating
    SELECT s.review_id AS record_id_str, 'Review Completed Without Rating' AS issue_type,
        'Review ' || s.review_id || ' for employee ' || s.employee_id || ' is Completed but has no rating' AS description,
        'Critical' AS severity, 'Enter rating before marking review Completed' AS recommended_action
    FROM base_performance_review_source_records s
    WHERE s.status = 'Completed' AND (s.rating IS NULL)
    UNION ALL
    -- 5. Rating outside allowed range
    SELECT s.review_id AS record_id_str, 'Rating Outside Allowed Range' AS issue_type,
        'Review ' || s.review_id || ' has rating ' || CAST(s.rating AS VARCHAR) || ' which is outside allowed range {min_rating}–{max_rating}' AS description,
        'Critical' AS severity, 'Correct rating to within 1.0–5.0 scale' AS recommended_action
    FROM base_performance_review_source_records s
    WHERE s.rating IS NOT NULL AND (s.rating < {min_rating} OR s.rating > {max_rating})
    UNION ALL
    -- 6. Review missing reviewer/manager
    SELECT s.review_id AS record_id_str, 'Review Missing Reviewer' AS issue_type,
        'Review ' || s.review_id || ' has no reviewer_id assigned' AS description,
        'Critical' AS severity, 'Assign a reviewer before finalizing review' AS recommended_action
    FROM base_performance_review_source_records s
    WHERE s.reviewer_id IS NULL OR TRIM(s.reviewer_id) = ''
    UNION ALL
    -- 7. Goal linked to unknown employee
    SELECT g.goal_id AS record_id_str, 'Goal Linked to Unknown Employee' AS issue_type,
        'Goal ' || g.goal_id || ' links to employee ' || g.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on goal record' AS recommended_action
    FROM base_performance_goal_source_records g
    WHERE g.employee_id NOT IN (SELECT employee_id FROM base_talent_employee_population)
    UNION ALL
    -- 8. Goal missing status
    SELECT g.goal_id AS record_id_str, 'Goal Missing Status' AS issue_type,
        'Goal ' || g.goal_id || ' for employee ' || g.employee_id || ' has no status' AS description,
        'Warning' AS severity, 'Set goal status (Completed/In Progress/Overdue etc.)' AS recommended_action
    FROM base_performance_goal_source_records g
    WHERE g.status IS NULL OR TRIM(g.status) = ''
    UNION ALL
    -- 9. Goal overdue
    SELECT g.goal_id AS record_id_str, 'Goal Overdue' AS issue_type,
        'Goal ' || g.goal_id || ' for employee ' || g.employee_id || ' is past due date ' || CAST(g.due_date AS VARCHAR) AS description,
        'Warning' AS severity, 'Resolve or update overdue goal' AS recommended_action
    FROM base_performance_goal_source_records g
    WHERE g.status NOT IN ('Completed', 'Cancelled') AND g.due_date < DATE '{tal_month_end}'
    UNION ALL
    -- 10. Competency assessment linked to unknown employee
    SELECT c.assessment_id AS record_id_str, 'Competency Linked to Unknown Employee' AS issue_type,
        'Assessment ' || c.assessment_id || ' links to employee ' || c.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on competency assessment' AS recommended_action
    FROM base_competency_source_records c
    WHERE c.employee_id NOT IN (SELECT employee_id FROM base_talent_employee_population)
    UNION ALL
    -- 11. Competency score outside allowed range
    SELECT c.assessment_id AS record_id_str, 'Competency Score Outside Range' AS issue_type,
        'Assessment ' || c.assessment_id || ' has score outside 1–5 (required=' || CAST(c.required_score AS VARCHAR) || ', actual=' || CAST(c.actual_score AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Correct competency scores to 1.0–5.0 range' AS recommended_action
    FROM base_competency_source_records c
    WHERE (c.required_score IS NOT NULL AND (c.required_score < {min_rating} OR c.required_score > {max_rating}))
       OR (c.actual_score IS NOT NULL AND (c.actual_score < {min_rating} OR c.actual_score > {max_rating}))
    UNION ALL
    -- 12. Critical role missing successor
    SELECT s.critical_role_id AS record_id_str, 'Critical Role Missing Successor' AS issue_type,
        'Critical role ' || s.role_title || ' (' || s.critical_role_id || ') has no nominated successor' AS description,
        'Warning' AS severity, 'Nominate a successor for this critical role' AS recommended_action
    FROM base_succession_plans_current s
    WHERE s.successor_employee_id IS NULL OR TRIM(s.successor_employee_id) = ''
    UNION ALL
    -- 13. Successor linked to unknown employee
    SELECT s.successor_employee_id AS record_id_str, 'Successor Linked to Unknown Employee' AS issue_type,
        'Succession plan ' || s.plan_id || ' successor ' || s.successor_employee_id || ' is not in employee master directory' AS description,
        'Critical' AS severity, 'Correct successor_employee_id in succession plan' AS recommended_action
    FROM base_succession_plans_current s
    WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
      AND s.successor_employee_id NOT IN (SELECT employee_id FROM base_active_workforce)
      AND s.successor_employee_id NOT IN (SELECT employee_id FROM base_talent_employee_population)
    UNION ALL
    -- 14. Successor assigned to inactive employee
    SELECT s.successor_employee_id AS record_id_str, 'Successor Assigned to Inactive Employee' AS issue_type,
        'Succession plan ' || s.plan_id || ' successor ' || s.successor_employee_id || ' is inactive or terminated' AS description,
        'Warning' AS severity, 'Reassign succession to an active employee' AS recommended_action
    FROM base_succession_plans_current s
    INNER JOIN (
        SELECT employee_id FROM employees WHERE status NOT IN ('Active')
    ) inactive ON s.successor_employee_id = inactive.employee_id
    UNION ALL
    -- 15. Successor readiness missing
    SELECT s.plan_id AS record_id_str, 'Successor Readiness Missing' AS issue_type,
        'Succession plan ' || s.plan_id || ' for role ' || s.role_title || ' has no readiness value' AS description,
        'Critical' AS severity, 'Set readiness status for this successor nomination' AS recommended_action
    FROM base_succession_plans_current s
    WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
      AND (s.readiness IS NULL OR TRIM(s.readiness) = '')
    UNION ALL
    -- 16. Training enrollment linked to unknown employee
    SELECT l.enrollment_id AS record_id_str, 'Enrollment Linked to Unknown Employee' AS issue_type,
        'Enrollment ' || l.enrollment_id || ' links to employee ' || l.employee_id || ' not in master directory' AS description,
        'Critical' AS severity, 'Correct employee_id on enrollment record' AS recommended_action
    FROM base_learning_source_records l
    WHERE l.employee_id NOT IN (SELECT employee_id FROM base_talent_employee_population)
    UNION ALL
    -- 17. Training completed without completion date
    SELECT l.enrollment_id AS record_id_str, 'Training Completed Without Date' AS issue_type,
        'Enrollment ' || l.enrollment_id || ' has status Completed but no completion_date' AS description,
        'Critical' AS severity, 'Set completion_date on completed enrollment' AS recommended_action
    FROM base_learning_source_records l
    WHERE l.status = 'Completed' AND l.completion_date IS NULL
    UNION ALL
    -- 18. Training hours missing or invalid
    SELECT t.course_id AS record_id_str, 'Training Hours Missing or Invalid' AS issue_type,
        'Course ' || t.course_name || ' has invalid/zero duration hours: ' || COALESCE(CAST(t.duration_hours AS VARCHAR), 'NULL') AS description,
        'Critical' AS severity, 'Enter valid positive training hours for this course' AS recommended_action
    FROM base_training_catalog_current t
    WHERE t.duration_hours IS NULL OR t.duration_hours <= 0
    UNION ALL
    -- 19. Learning course missing category
    SELECT t.course_id AS record_id_str, 'Learning Course Missing Category' AS issue_type,
        'Course ' || t.course_name || ' has no category assigned' AS description,
        'Warning' AS severity, 'Assign a category to this training course' AS recommended_action
    FROM base_training_catalog_current t
    WHERE t.category IS NULL OR TRIM(t.category) = ''
    UNION ALL
    -- 20. Talent review missing potential rating
    SELECT tr.employee_id AS record_id_str, 'Talent Review Missing Potential Rating' AS issue_type,
        'Talent review for employee ' || tr.employee_id || ' is missing the potential_rating field' AS description,
        'Critical' AS severity, 'Enter potential rating on talent review record' AS recommended_action
    FROM base_talent_review_source_records tr
    WHERE tr.potential_rating IS NULL OR TRIM(tr.potential_rating) = ''
    UNION ALL
    -- 21. High performer with high flight risk
    SELECT pr.employee_id AS record_id_str, 'High Performer With High Flight Risk' AS issue_type,
        'Employee ' || pr.employee_id || ' is rated ' || pr.performance_category || ' but has high flight risk' AS description,
        'Warning' AS severity, 'Engage retention measures for this high-performer' AS recommended_action
    FROM base_performance_reviews_current pr
    INNER JOIN base_talent_reviews_current tr ON pr.employee_id = tr.employee_id
    WHERE pr.performance_category IN ('Outstanding', 'Exceeds Expectations') AND tr.flight_risk = 'High'
    UNION ALL
    -- 22. Critical employee without successor
    SELECT e.employee_id AS record_id_str, 'Critical Employee Without Successor' AS issue_type,
        'Employee ' || e.employee_id || ' (' || e.job_title || ') is in a critical role but has no succession plan' AS description,
        'Warning' AS severity, 'Create a succession plan for this critical employee' AS recommended_action
    FROM base_talent_employee_population e
    WHERE e.job_title IN ({critical_titles_sql if critical_titles_sql else "''"})
      AND e.employee_id NOT IN (
          SELECT DISTINCT current_employee_id FROM base_succession_plans_current
          WHERE successor_employee_id IS NOT NULL AND TRIM(successor_employee_id) != ''
      )
    UNION ALL
    -- 23. Duplicate skill record
    SELECT s.employee_id AS record_id_str, 'Duplicate Skill Record' AS issue_type,
        'Employee ' || s.employee_id || ' has duplicate entry for skill: ' || s.skill_name AS description,
        'Warning' AS severity, 'Deduplicate employee skill records' AS recommended_action
    FROM base_employee_skill_source_records s
    WHERE EXISTS (
        SELECT 1 FROM base_employee_skill_source_records s2
        WHERE s2.employee_id = s.employee_id AND s2.skill_name = s.skill_name
        GROUP BY s2.employee_id, s2.skill_name HAVING COUNT(*) > 1
    )
    UNION ALL
    -- 24. Career path missing next role
    SELECT cp.employee_id AS record_id_str, 'Career Path Missing Next Role' AS issue_type,
        'Career path for employee ' || cp.employee_id || ' has no next_role defined' AS description,
        'Warning' AS severity, 'Define the next_role for this career path entry' AS recommended_action
    FROM career_paths cp
    WHERE cp.next_role IS NULL OR TRIM(cp.next_role) = '';
    """)
    print("Created view 'mart_talent_exceptions'")

    # mart_talent_kpis
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_talent_kpis AS
    WITH talent_pop AS (SELECT COUNT(*) AS total FROM base_talent_employee_population),
    reviewed AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM base_performance_reviews_current),
    avg_rating AS (SELECT ROUND(AVG(rating), 2) AS avg_r FROM base_performance_reviews_current),
    high_perf AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM base_performance_reviews_current WHERE performance_category IN ('Outstanding', 'Exceeds Expectations')),
    low_perf  AS (SELECT COUNT(DISTINCT employee_id) AS cnt FROM base_performance_reviews_current WHERE performance_category IN ('Needs Improvement', 'Unsatisfactory')),
    goals AS (
        SELECT
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) AS completed_goals,
            COUNT(CASE WHEN status != 'Cancelled' THEN 1 END) AS eligible_goals
        FROM base_performance_goals_current
    ),
    learning AS (
        SELECT
            COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enr,
            COUNT(CASE WHEN l.status != 'Cancelled' THEN 1 END) AS eligible_enr,
            COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours,
            COUNT(DISTINCT CASE WHEN l.status = 'Completed' THEN l.employee_id END) AS unique_trainees
        FROM base_learning_enrollments_current l
        LEFT JOIN base_training_catalog_current t ON l.course_id = t.course_id
    ),
    succession AS (
        WITH valid_successors AS (
            SELECT DISTINCT critical_role_id
            FROM base_succession_plans_current s
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        )
        SELECT
            COUNT(DISTINCT critical_role_id) AS total_roles
        FROM base_succession_plans_current
    ),
    covered_roles AS (
        SELECT COUNT(DISTINCT critical_role_id) AS covered
        FROM base_succession_plans_current s
        WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
          AND s.successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
          AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
    ),
    ready_now AS (
        SELECT COUNT(DISTINCT successor_employee_id) AS cnt
        FROM base_succession_plans_current
        WHERE readiness = 'Ready Now'
          AND successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
    ),
    exc_count AS (SELECT COUNT(*) AS cnt FROM mart_talent_exceptions)
    SELECT
        CAST(reviewed.cnt AS DOUBLE) AS employees_reviewed,
        CASE WHEN talent_pop.total = 0 THEN 0.0
             ELSE ROUND(100.0 * reviewed.cnt / talent_pop.total, 2) END AS review_completion_pct,
        avg_rating.avg_r AS average_performance_rating,
        CAST(high_perf.cnt AS DOUBLE) AS high_performers,
        CAST(low_perf.cnt AS DOUBLE) AS low_performers,
        CASE WHEN goals.eligible_goals = 0 THEN 0.0
             ELSE ROUND(100.0 * goals.completed_goals / goals.eligible_goals, 2) END AS goal_completion_pct,
        CASE WHEN learning.eligible_enr = 0 THEN 0.0
             ELSE ROUND(100.0 * learning.completed_enr / learning.eligible_enr, 2) END AS training_completion_pct,
        CASE WHEN learning.unique_trainees = 0 THEN 0.0
             ELSE ROUND(learning.total_hours / learning.unique_trainees, 2) END AS average_training_hours,
        CASE WHEN succession.total_roles = 0 THEN 100.0
             ELSE ROUND(100.0 * covered_roles.covered / succession.total_roles, 2) END AS critical_roles_covered_pct,
        CAST(ready_now.cnt AS DOUBLE) AS ready_successors,
        CAST(exc_count.cnt AS DOUBLE) AS talent_exception_count
    FROM talent_pop, reviewed, avg_rating, high_perf, low_perf, goals, learning, succession, covered_roles, ready_now, exc_count;
    """)
    print("Created view 'mart_talent_kpis'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_performance_distribution AS
    SELECT performance_category, COUNT(DISTINCT employee_id) AS employee_count
    FROM base_performance_reviews_current
    GROUP BY performance_category;
    """)
    print("Created view 'mart_performance_distribution'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_performance_by_project AS
    SELECT e.project,
        COUNT(DISTINCT pr.employee_id) AS reviewed_count,
        ROUND(AVG(pr.rating), 2) AS average_rating,
        COUNT(CASE WHEN pr.performance_category IN ('Outstanding', 'Exceeds Expectations') THEN 1 END) AS high_performers,
        COUNT(CASE WHEN pr.performance_category IN ('Needs Improvement', 'Unsatisfactory') THEN 1 END) AS low_performers
    FROM base_performance_reviews_current pr
    JOIN base_talent_employee_population e ON pr.employee_id = e.employee_id
    GROUP BY e.project;
    """)
    print("Created view 'mart_performance_by_project'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_performance_by_department AS
    SELECT e.department,
        COUNT(DISTINCT pr.employee_id) AS reviewed_count,
        ROUND(AVG(pr.rating), 2) AS average_rating,
        COUNT(CASE WHEN pr.performance_category IN ('Outstanding', 'Exceeds Expectations') THEN 1 END) AS high_performers,
        COUNT(CASE WHEN pr.performance_category IN ('Needs Improvement', 'Unsatisfactory') THEN 1 END) AS low_performers
    FROM base_performance_reviews_current pr
    JOIN base_talent_employee_population e ON pr.employee_id = e.employee_id
    GROUP BY e.department;
    """)
    print("Created view 'mart_performance_by_department'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_goal_completion AS
    SELECT
        COALESCE(e.department, 'Unknown') AS department,
        COUNT(CASE WHEN g.status = 'Completed' THEN 1 END) AS completed_goals,
        COUNT(CASE WHEN g.status = 'In Progress' THEN 1 END) AS in_progress_goals,
        COUNT(CASE WHEN g.status = 'Overdue' THEN 1 END) AS overdue_goals,
        COUNT(CASE WHEN g.status = 'Not Started' THEN 1 END) AS not_started_goals,
        COUNT(CASE WHEN g.status = 'Cancelled' THEN 1 END) AS cancelled_goals,
        COUNT(CASE WHEN g.status != 'Cancelled' THEN 1 END) AS eligible_goals
    FROM base_performance_goals_current g
    LEFT JOIN base_talent_employee_population e ON g.employee_id = e.employee_id
    GROUP BY e.department;
    """)
    print("Created view 'mart_goal_completion'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_competency_gaps AS
    SELECT
        competency_name,
        ROUND(AVG(required_score), 2) AS avg_required,
        ROUND(AVG(actual_score), 2) AS avg_actual,
        ROUND(AVG(required_score - actual_score), 2) AS avg_gap
    FROM base_competency_assessments_current
    GROUP BY competency_name
    ORDER BY avg_gap DESC;
    """)
    print("Created view 'mart_competency_gaps'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_learning_completion AS
    SELECT
        COALESCE(t.category, 'Uncategorized') AS category,
        COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enrollments,
        COUNT(CASE WHEN l.status != 'Cancelled' THEN 1 END) AS eligible_enrollments,
        COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours
    FROM base_learning_enrollments_current l
    LEFT JOIN base_training_catalog_current t ON l.course_id = t.course_id
    GROUP BY t.category;
    """)
    print("Created view 'mart_learning_completion'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_learning_by_project AS
    SELECT
        COALESCE(e.project, 'Unassigned') AS project,
        COALESCE(e.department, 'Unknown') AS department,
        COUNT(CASE WHEN l.status = 'Completed' THEN 1 END) AS completed_enrollments,
        COALESCE(SUM(CASE WHEN l.status = 'Completed' THEN t.duration_hours ELSE 0 END), 0) AS total_hours
    FROM base_learning_enrollments_current l
    LEFT JOIN base_talent_employee_population e ON l.employee_id = e.employee_id
    LEFT JOIN base_training_catalog_current t ON l.course_id = t.course_id
    GROUP BY e.project, e.department;
    """)
    print("Created view 'mart_learning_by_project'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_succession_coverage AS
    SELECT
        s.critical_role_id,
        s.role_title,
        COUNT(DISTINCT s.successor_employee_id) FILTER (
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        ) AS valid_successor_count,
        CASE WHEN COUNT(DISTINCT s.successor_employee_id) FILTER (
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        ) > 0 THEN 'Covered' ELSE 'Not Covered' END AS coverage_status
    FROM base_succession_plans_current s
    GROUP BY s.critical_role_id, s.role_title;
    """)
    print("Created view 'mart_succession_coverage'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_successor_readiness AS
    SELECT
        COALESCE(readiness, 'Missing') AS readiness,
        COUNT(DISTINCT successor_employee_id) AS successor_count
    FROM base_succession_plans_current
    WHERE successor_employee_id IS NOT NULL AND TRIM(successor_employee_id) != ''
    GROUP BY readiness;
    """)
    print("Created view 'mart_successor_readiness'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_talent_risk AS
    SELECT
        pr.employee_id,
        COALESCE(e.department, 'Unknown') AS department,
        COALESCE(e.project, 'Unassigned') AS project,
        pr.performance_category,
        COALESCE(tr.potential_rating, 'Unknown') AS potential_rating,
        COALESCE(tr.flight_risk, 'Unknown') AS flight_risk,
        CASE
            WHEN tr.flight_risk = 'High' AND (tr.potential_rating = 'High' OR pr.performance_category IN ('Outstanding', 'Exceeds Expectations'))
                THEN 'High Risk'
            WHEN (tr.flight_risk = 'High' AND tr.potential_rating NOT IN ('High') AND pr.performance_category NOT IN ('Outstanding', 'Exceeds Expectations'))
              OR (tr.flight_risk = 'Medium' AND (tr.potential_rating IN ('High', 'Medium') OR pr.performance_category IN ('Outstanding', 'Exceeds Expectations', 'Meets Expectations')))
                THEN 'Medium Risk'
            ELSE 'Low Risk'
        END AS risk_category
    FROM base_performance_reviews_current pr
    LEFT JOIN base_talent_reviews_current tr ON pr.employee_id = tr.employee_id
    LEFT JOIN base_talent_employee_population e ON pr.employee_id = e.employee_id;
    """)
    print("Created view 'mart_talent_risk'")

    # Trends (simulated: add prior months as static, current period from real data)
    conn.execute(f"""
    CREATE OR REPLACE VIEW mart_talent_review_trends AS
    SELECT '2026-04' AS period, 12 AS total_reviewed, 10 AS completed_reviews, 85.0 AS completion_pct, 3.6 AS avg_rating
    UNION ALL
    SELECT '2026-05' AS period, 14 AS total_reviewed, 12 AS completed_reviews, 88.0 AS completion_pct, 3.7 AS avg_rating
    UNION ALL
    SELECT '{talent_report_month}' AS period,
        (SELECT COUNT(*) FROM base_talent_employee_population) AS total_reviewed,
        (SELECT COUNT(DISTINCT employee_id) FROM base_performance_reviews_current) AS completed_reviews,
        (SELECT CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE ROUND(100.0 * COUNT(DISTINCT employee_id) / COUNT(*) OVER (), 2) END
            FROM base_talent_employee_population LIMIT 1) AS completion_pct,
        (SELECT ROUND(AVG(rating), 2) FROM base_performance_reviews_current) AS avg_rating;
    """)
    print("Created view 'mart_talent_review_trends'")

    # ---- Talent Reconciliation Assertions -----
    print("Running Talent & Succession reconciliation checks...")
    try:
        kpi_row = conn.execute("""
            SELECT employees_reviewed, review_completion_pct, average_performance_rating,
                   high_performers, low_performers, goal_completion_pct, training_completion_pct,
                   average_training_hours, critical_roles_covered_pct, ready_successors,
                   talent_exception_count
            FROM mart_talent_kpis
        """).fetchone()
        kpi_reviewed, kpi_completion_pct, kpi_avg_rating, kpi_high, kpi_low, kpi_goal_pct, \
        kpi_train_pct, kpi_avg_hours, kpi_coverage_pct, kpi_ready, kpi_exc = kpi_row

        # 1. Employees Reviewed
        actual_reviewed = conn.execute("SELECT COUNT(DISTINCT employee_id) FROM base_performance_reviews_current").fetchone()[0]
        print(f"Employees Reviewed KPI: {kpi_reviewed}, Calculated: {actual_reviewed}")
        if int(kpi_reviewed) != actual_reviewed:
            raise ValueError(f"CRITICAL: Employees Reviewed KPI ({kpi_reviewed}) != calculated ({actual_reviewed})")

        # 2. Review Completion %
        talent_pop_count = conn.execute("SELECT COUNT(*) FROM base_talent_employee_population").fetchone()[0]
        expected_pct = round(100.0 * actual_reviewed / talent_pop_count, 2) if talent_pop_count > 0 else 0.0
        print(f"Review Completion % KPI: {kpi_completion_pct}, Expected: {expected_pct}%")
        if abs(kpi_completion_pct - expected_pct) > 0.1:
            raise ValueError(f"CRITICAL: Review Completion % KPI ({kpi_completion_pct}) != expected ({expected_pct})")

        # 3. Average Performance Rating
        actual_avg = conn.execute("SELECT ROUND(AVG(rating), 2) FROM base_performance_reviews_current").fetchone()[0]
        print(f"Average Performance Rating KPI: {kpi_avg_rating}, Calculated: {actual_avg}")
        if actual_avg and abs(kpi_avg_rating - actual_avg) > 0.01:
            raise ValueError(f"CRITICAL: Avg Performance Rating KPI ({kpi_avg_rating}) != calculated ({actual_avg})")

        # 4. Performance Distribution Total
        dist_total = conn.execute("SELECT SUM(employee_count) FROM mart_performance_distribution").fetchone()[0] or 0
        print(f"Performance Distribution Total: {dist_total}, Completed Reviews: {actual_reviewed}")
        if dist_total != actual_reviewed:
            raise ValueError(f"CRITICAL: Performance distribution sum ({dist_total}) != reviewed employees ({actual_reviewed})")

        # 5. High Performer Count
        actual_high = conn.execute("SELECT COUNT(DISTINCT employee_id) FROM base_performance_reviews_current WHERE performance_category IN ('Outstanding', 'Exceeds Expectations')").fetchone()[0]
        print(f"High Performers KPI: {kpi_high}, Calculated: {actual_high}")
        if int(kpi_high) != actual_high:
            raise ValueError(f"CRITICAL: High Performers KPI ({kpi_high}) != calculated ({actual_high})")

        # 6. Low Performer Count
        actual_low = conn.execute("SELECT COUNT(DISTINCT employee_id) FROM base_performance_reviews_current WHERE performance_category IN ('Needs Improvement', 'Unsatisfactory')").fetchone()[0]
        print(f"Low Performers KPI: {kpi_low}, Calculated: {actual_low}")
        if int(kpi_low) != actual_low:
            raise ValueError(f"CRITICAL: Low Performers KPI ({kpi_low}) != calculated ({actual_low})")

        # 7. Goal Completion %
        completed_goals = conn.execute("SELECT COUNT(*) FROM base_performance_goals_current WHERE status = 'Completed'").fetchone()[0]
        eligible_goals = conn.execute("SELECT COUNT(*) FROM base_performance_goals_current WHERE status != 'Cancelled'").fetchone()[0]
        expected_goal_pct = round(100.0 * completed_goals / eligible_goals, 2) if eligible_goals > 0 else 0.0
        print(f"Goal Completion % KPI: {kpi_goal_pct}, Expected: {expected_goal_pct}%")
        if abs(kpi_goal_pct - expected_goal_pct) > 0.1:
            raise ValueError(f"CRITICAL: Goal Completion % KPI ({kpi_goal_pct}) != expected ({expected_goal_pct})")

        # 8. Training Completion %
        completed_enr = conn.execute("SELECT COUNT(*) FROM base_learning_enrollments_current WHERE status = 'Completed'").fetchone()[0]
        eligible_enr = conn.execute("SELECT COUNT(*) FROM base_learning_enrollments_current WHERE status != 'Cancelled'").fetchone()[0]
        expected_train_pct = round(100.0 * completed_enr / eligible_enr, 2) if eligible_enr > 0 else 0.0
        print(f"Training Completion % KPI: {kpi_train_pct}, Expected: {expected_train_pct}%")
        if abs(kpi_train_pct - expected_train_pct) > 0.1:
            raise ValueError(f"CRITICAL: Training Completion % KPI ({kpi_train_pct}) != expected ({expected_train_pct})")

        # 9. Average Training Hours
        total_hours = conn.execute("""
            SELECT COALESCE(SUM(t.duration_hours), 0)
            FROM base_learning_enrollments_current l
            LEFT JOIN base_training_catalog_current t ON l.course_id = t.course_id
            WHERE l.status = 'Completed'
        """).fetchone()[0]
        unique_trainees = conn.execute("SELECT COUNT(DISTINCT employee_id) FROM base_learning_enrollments_current WHERE status = 'Completed'").fetchone()[0]
        expected_avg_hours = round(total_hours / unique_trainees, 2) if unique_trainees > 0 else 0.0
        print(f"Average Training Hours KPI: {kpi_avg_hours}, Expected: {expected_avg_hours}")
        if abs(kpi_avg_hours - expected_avg_hours) > 0.1:
            raise ValueError(f"CRITICAL: Average Training Hours KPI ({kpi_avg_hours}) != expected ({expected_avg_hours})")

        # 10. Critical Roles Covered %
        total_crit_roles = conn.execute("SELECT COUNT(DISTINCT critical_role_id) FROM base_succession_plans_current").fetchone()[0]
        covered_crit_roles = conn.execute("""
            SELECT COUNT(DISTINCT critical_role_id)
            FROM base_succession_plans_current s
            WHERE s.successor_employee_id IS NOT NULL AND TRIM(s.successor_employee_id) != ''
              AND s.successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
              AND s.readiness IS NOT NULL AND TRIM(s.readiness) != ''
        """).fetchone()[0]
        expected_coverage_pct = round(100.0 * covered_crit_roles / total_crit_roles, 2) if total_crit_roles > 0 else 100.0
        print(f"Critical Roles Covered % KPI: {kpi_coverage_pct}, Expected: {expected_coverage_pct}%")
        if abs(kpi_coverage_pct - expected_coverage_pct) > 0.1:
            raise ValueError(f"CRITICAL: Critical Roles Covered % KPI ({kpi_coverage_pct}) != expected ({expected_coverage_pct})")

        # 11. Ready Successors
        actual_ready = conn.execute("""
            SELECT COUNT(DISTINCT successor_employee_id)
            FROM base_succession_plans_current
            WHERE readiness = 'Ready Now'
              AND successor_employee_id IN (SELECT employee_id FROM base_talent_employee_population)
        """).fetchone()[0]
        print(f"Ready Successors KPI: {kpi_ready}, Calculated: {actual_ready}")
        if int(kpi_ready) != actual_ready:
            raise ValueError(f"CRITICAL: Ready Successors KPI ({kpi_ready}) != calculated ({actual_ready})")

        # 12. Project / Department Totals
        sum_proj = conn.execute("SELECT SUM(reviewed_count) FROM mart_performance_by_project").fetchone()[0] or 0
        print(f"Sum Project Reviewed: {sum_proj}, Total Reviewed: {actual_reviewed}")
        if sum_proj != actual_reviewed:
            raise ValueError(f"CRITICAL: Project reviewed sum ({sum_proj}) != total reviewed ({actual_reviewed})")

        # 13. Talent Exception Count
        actual_exc = conn.execute("SELECT COUNT(*) FROM mart_talent_exceptions").fetchone()[0]
        print(f"Talent Exception Count KPI: {kpi_exc}, Calculated: {actual_exc}")
        if int(kpi_exc) != actual_exc:
            raise ValueError(f"CRITICAL: Talent Exception Count KPI ({kpi_exc}) != calculated ({actual_exc})")

        print("Talent & Succession reconciliation checks PASSED.")
    except Exception as e:
        print(f"Talent reconciliation check FAILED: {str(e)}")
        raise e

    # -------------------------------------------------------------
    # Milestone 2H: Command Center Integration & Health Marts
    # -------------------------------------------------------------
    cc_rules = rules.get("command_center_rules", {})
    cc_report_month = cc_rules.get("report_month", "2026-06")
    try:
        year, month = map(int, cc_report_month.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        cc_report_month_end = f"{cc_report_month}-{last_day:02d}"
    except Exception:
        cc_report_month_end = f"{cc_report_month}-30"
    cc_report_month_start = f"{cc_report_month}-01"

    print(f"Using Command Center report month: {cc_report_month}")

    conn.execute(f"""
    CREATE OR REPLACE VIEW base_command_center_report_context AS
    SELECT 
        '{cc_report_month}' AS report_month,
        '{cc_report_month_start}' AS report_month_start,
        '{cc_report_month_end}' AS report_month_end,
        CAST(now() AS TIMESTAMP) AS last_refresh_timestamp;
    """)
    print("Created view 'base_command_center_report_context'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_command_center_module_registry AS
    SELECT 'executive' AS module_key, 'executive' AS page_key, 'Executive Summary' AS module_label, '/executive' AS route_path, 'Executive' AS owner_domain, 8 AS primary_kpi_count, 'docs/qa/screenshots/milestone_1_executive_summary.png' AS screenshot_path, 'docs/qa/reports/executive_summary_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'data-quality' AS module_key, 'data-quality' AS page_key, 'Data Quality' AS module_label, '/data-quality' AS route_path, 'Data Quality' AS owner_domain, 7 AS primary_kpi_count, 'docs/qa/screenshots/milestone_1_data_quality.png' AS screenshot_path, 'docs/qa/reports/qa_report.md' AS qa_report_path UNION ALL
    SELECT 'workforce' AS module_key, 'workforce' AS page_key, 'Workforce' AS module_label, '/workforce' AS route_path, 'Workforce' AS owner_domain, 5 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2a_workforce_dashboard.png' AS screenshot_path, 'docs/qa/reports/workforce_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'payroll' AS module_key, 'payroll' AS page_key, 'Payroll & Cost' AS module_label, '/payroll' AS route_path, 'Payroll' AS owner_domain, 5 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2b_payroll_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2b_payroll_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'attendance' AS module_key, 'attendance' AS page_key, 'Attendance' AS module_label, '/attendance' AS route_path, 'Attendance' AS owner_domain, 5 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2c_attendance_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2c_attendance_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'compliance' AS module_key, 'compliance' AS page_key, 'Saudization & Compliance' AS module_label, '/compliance' AS route_path, 'Compliance' AS owner_domain, 6 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2d_compliance_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2d_compliance_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'er' AS module_key, 'er' AS page_key, 'Employee Relations' AS module_label, '/er' AS route_path, 'Employee Relations' AS owner_domain, 6 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2e_er_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2e_er_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'recruitment' AS module_key, 'recruitment' AS page_key, 'Recruitment & Hiring' AS module_label, '/recruitment' AS route_path, 'Recruitment' AS owner_domain, 7 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2f_recruitment_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2f_recruitment_qa_report.md' AS qa_report_path UNION ALL
    SELECT 'talent' AS module_key, 'talent' AS page_key, 'Talent & Succession' AS module_label, '/talent' AS route_path, 'Talent' AS owner_domain, 11 AS primary_kpi_count, 'docs/qa/screenshots/milestone_2g_talent_dashboard.png' AS screenshot_path, 'docs/qa/reports/milestone_2g_talent_qa_report.md' AS qa_report_path;
    """)
    print("Created view 'base_command_center_module_registry'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_command_exception_data_quality AS
    SELECT 'data-quality' AS module_key, 'Data Quality' AS module_label, 'mart_data_quality_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/data-quality' AS route_path FROM mart_data_quality_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_workforce AS
    SELECT 'workforce' AS module_key, 'Workforce' AS module_label, 'mart_workforce_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/workforce' AS route_path FROM mart_workforce_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_payroll AS
    SELECT 'payroll' AS module_key, 'Payroll & Cost' AS module_label, 'mart_payroll_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/payroll' AS route_path FROM mart_payroll_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_attendance AS
    SELECT 'attendance' AS module_key, 'Attendance' AS module_label, 'mart_attendance_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/attendance' AS route_path FROM mart_attendance_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_compliance AS
    SELECT 'compliance' AS module_key, 'Saudization & Compliance' AS module_label, 'mart_compliance_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/compliance' AS route_path FROM mart_compliance_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_er AS
    SELECT 'er' AS module_key, 'Employee Relations' AS module_label, 'mart_er_exceptions' AS source_mart, case_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/er' AS route_path FROM mart_er_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_recruitment AS
    SELECT 'recruitment' AS module_key, 'Recruitment & Hiring' AS module_label, 'mart_recruitment_exceptions' AS source_mart, record_id_str AS entity_id, CAST(NULL AS VARCHAR) AS entity_name, issue_type, description, severity, recommended_action, '/recruitment' AS route_path FROM mart_recruitment_exceptions;

    CREATE OR REPLACE VIEW base_command_exception_talent AS
    SELECT 'talent' AS module_key, 'Talent & Succession' AS module_label, 'mart_talent_exceptions' AS source_mart, record_id_str AS entity_id, CAST(NULL AS VARCHAR) AS entity_name, issue_type, description, severity, recommended_action, '/talent' AS route_path FROM mart_talent_exceptions;
    """)
    print("Created views base_command_exception_*")

    conn.execute("""
    CREATE OR REPLACE VIEW base_command_center_exception_sources AS
    WITH raw_exceptions AS (
        SELECT * FROM base_command_exception_data_quality UNION ALL
        SELECT * FROM base_command_exception_workforce UNION ALL
        SELECT * FROM base_command_exception_payroll UNION ALL
        SELECT * FROM base_command_exception_attendance UNION ALL
        SELECT * FROM base_command_exception_compliance UNION ALL
        SELECT * FROM base_command_exception_er UNION ALL
        SELECT * FROM base_command_exception_recruitment UNION ALL
        SELECT * FROM base_command_exception_talent
    )
    SELECT 
        module_key,
        module_label,
        source_mart,
        entity_id,
        entity_name,
        issue_type,
        description,
        CASE LOWER(TRIM(severity))
            WHEN 'critical' THEN 'Critical'
            WHEN 'warning' THEN 'Warning'
            WHEN 'info' THEN 'Info'
            ELSE 'Unknown'
        END AS severity,
        recommended_action,
        route_path
    FROM raw_exceptions;
    """)
    print("Created view 'base_command_center_exception_sources'")

    conn.execute("""
    CREATE OR REPLACE VIEW base_command_center_data_freshness AS
    SELECT 'payroll' AS module_key, 'payroll' AS source_table, CAST(MAX(payroll_period) AS VARCHAR) AS max_source_date FROM payroll UNION ALL
    SELECT 'attendance' AS module_key, 'attendance' AS source_table, CAST(MAX(attendance_date) AS VARCHAR) AS max_source_date FROM attendance UNION ALL
    SELECT 'recruitment' AS module_key, 'recruitment_requisitions' AS source_table, CAST(MAX(approval_date) AS VARCHAR) AS max_source_date FROM recruitment_requisitions UNION ALL
    SELECT 'talent' AS module_key, 'performance_reviews' AS source_table, CAST(MAX(completed_date) AS VARCHAR) AS max_source_date FROM performance_reviews UNION ALL
    SELECT 'compliance' AS module_key, 'compliance' AS source_table, CAST(MAX(period) AS VARCHAR) AS max_source_date FROM compliance UNION ALL
    SELECT 'er' AS module_key, 'employee_relations' AS source_table, CAST(MAX(COALESCE(closed_date, created_date)) AS VARCHAR) AS max_source_date FROM employee_relations UNION ALL
    SELECT 'workforce' AS module_key, 'employees' AS source_table, CAST(MAX(joining_date) AS VARCHAR) AS max_source_date FROM employees;
    """)
    print("Created view 'base_command_center_data_freshness'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_data_freshness AS
    WITH raw_fresh AS (
        SELECT 
            f.module_key,
            f.source_table,
            f.max_source_date,
            CASE 
                WHEN f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = 'payroll' AND f.max_source_date < c.report_month THEN TRUE
                WHEN f.module_key = 'attendance' AND CAST(f.max_source_date AS DATE) < CAST(c.report_month_end AS DATE) THEN TRUE
                WHEN f.module_key = 'recruitment' AND f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = 'talent' AND f.max_source_date IS NULL THEN TRUE
                WHEN f.module_key = 'compliance' AND f.max_source_date < c.report_month THEN TRUE
                WHEN f.module_key = 'er' AND f.max_source_date < c.report_month THEN TRUE
                ELSE FALSE
            END AS stale_flag,
            CASE 
                WHEN f.max_source_date IS NULL THEN 'No transaction data found in source table'
                WHEN f.module_key = 'payroll' AND f.max_source_date < c.report_month THEN 'Payroll period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                WHEN f.module_key = 'attendance' AND CAST(f.max_source_date AS DATE) < CAST(c.report_month_end AS DATE) THEN 'Attendance date ' || f.max_source_date || ' is older than expected report month end ' || c.report_month_end
                WHEN f.module_key = 'recruitment' AND f.max_source_date IS NULL THEN 'Recruitment requisitions data is missing'
                WHEN f.module_key = 'talent' AND f.max_source_date IS NULL THEN 'Talent reviews data is missing'
                WHEN f.module_key = 'compliance' AND f.max_source_date < c.report_month THEN 'Compliance period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                WHEN f.module_key = 'er' AND f.max_source_date < c.report_month THEN 'ER period ' || f.max_source_date || ' is older than expected report month ' || c.report_month
                ELSE 'Data is current'
            END AS stale_reason
        FROM base_command_center_data_freshness f
        CROSS JOIN base_command_center_report_context c
    )
    SELECT 
        reg.module_key,
        reg.module_label,
        COALESCE(rf.source_table, CASE reg.module_key WHEN 'executive' THEN 'mart_exec_kpis' WHEN 'data-quality' THEN 'data_quality' ELSE 'derived' END) AS source_table,
        COALESCE(rf.max_source_date, CAST(c.report_month_end AS VARCHAR)) AS max_source_date,
        c.last_refresh_timestamp,
        CASE reg.module_key
            WHEN 'executive' THEN COALESCE((SELECT bool_or(stale_flag) FROM raw_fresh), FALSE)
            WHEN 'data-quality' THEN FALSE
            ELSE COALESCE(rf.stale_flag, FALSE)
        END AS stale_flag,
        CASE reg.module_key
            WHEN 'executive' THEN 'Derived from overall system state'
            WHEN 'data-quality' THEN 'Refreshed during DQ pipeline run'
            ELSE COALESCE(rf.stale_reason, 'Data is current')
        END AS stale_reason
    FROM base_command_center_module_registry reg
    CROSS JOIN base_command_center_report_context c
    LEFT JOIN raw_fresh rf ON reg.module_key = rf.module_key;
    """)
    print("Created view 'mart_command_center_data_freshness'")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS command_center_module_checks (
        module_key VARCHAR PRIMARY KEY,
        api_health_status VARCHAR,
        reconciliation_status VARCHAR,
        required_marts_present BOOLEAN,
        page_render_status VARCHAR,
        last_checked_at TIMESTAMP
    );
    """)

    conn.execute("""
    INSERT INTO command_center_module_checks (module_key, api_health_status, reconciliation_status, required_marts_present, page_render_status, last_checked_at)
    SELECT module_key, 'Unknown', 'Unknown', FALSE, 'Unknown', CAST(NULL AS TIMESTAMP)
    FROM base_command_center_module_registry
    WHERE module_key NOT IN (SELECT module_key FROM command_center_module_checks);
    """)

    conn.execute("""
    CREATE OR REPLACE VIEW base_command_center_module_status AS
    WITH errs AS (
        SELECT 
            module_key,
            COUNT(CASE WHEN severity = 'Critical' THEN 1 END) AS critical_exception_count,
            COUNT(CASE WHEN severity = 'Warning' THEN 1 END) AS warning_exception_count
        FROM base_command_center_exception_sources
        GROUP BY module_key
    ),
    fresh AS (
        SELECT 
            module_key, 
            stale_flag
        FROM mart_command_center_data_freshness
    )
    SELECT 
        reg.module_key,
        reg.module_label,
        reg.route_path,
        reg.owner_domain,
        COALESCE(chk.api_health_status, 'Unknown') AS api_health_status,
        COALESCE(chk.reconciliation_status, 'Unknown') AS reconciliation_status,
        COALESCE(chk.required_marts_present, FALSE) AS required_marts_present,
        COALESCE(f.stale_flag, FALSE) AS stale_flag,
        COALESCE(e.critical_exception_count, 0) AS critical_exception_count,
        COALESCE(e.warning_exception_count, 0) AS warning_exception_count,
        reg.primary_kpi_count,
        reg.screenshot_path,
        reg.qa_report_path
    FROM base_command_center_module_registry reg
    LEFT JOIN errs e ON reg.module_key = e.module_key
    LEFT JOIN fresh f ON reg.module_key = f.module_key
    LEFT JOIN command_center_module_checks chk ON reg.module_key = chk.module_key;
    """)
    print("Created view 'base_command_center_module_status'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_module_health AS
    SELECT 
        module_key,
        module_label,
        route_path,
        owner_domain,
        api_health_status,
        reconciliation_status,
        required_marts_present,
        stale_flag,
        critical_exception_count,
        warning_exception_count,
        CASE 
            WHEN api_health_status = 'Unhealthy' OR required_marts_present = FALSE OR reconciliation_status = 'Failed' OR critical_exception_count > 0 THEN 'Critical'
            WHEN api_health_status = 'Unknown' OR reconciliation_status = 'Unknown' THEN 'Unknown'
            WHEN warning_exception_count > 0 OR stale_flag = TRUE THEN 'Warning'
            WHEN api_health_status = 'Healthy' AND required_marts_present = TRUE AND reconciliation_status = 'Passed' AND stale_flag = FALSE AND critical_exception_count = 0 AND warning_exception_count = 0 THEN 'Healthy'
            ELSE 'Unknown'
        END AS status,
        primary_kpi_count,
        screenshot_path,
        qa_report_path
    FROM base_command_center_module_status;
    """)
    print("Created view 'mart_command_center_module_health'")

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
    
    # Retrieve values in Python to avoid DuckDB query planning deadlocks
    cc_active_headcount = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
    cc_payroll_cost = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
    cc_attendance_compliance_pct = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
    cc_saudization_pct = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
    cc_open_er_cases = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
    cc_open_requisitions = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
    cc_review_completion_pct = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
    cc_total_active_exceptions = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
    cc_modules_healthy = conn.execute("SELECT COUNT(*) FROM mart_command_center_module_health WHERE status = 'Healthy'").fetchone()[0]
    cc_last_data_refresh = conn.execute("SELECT last_refresh_timestamp FROM base_command_center_report_context").fetchone()[0]
    cc_latest_source_business_date = conn.execute("SELECT MAX(max_source_date) FROM base_command_center_data_freshness").fetchone()[0]
    cc_data_quality_score = conn.execute("SELECT data_quality_score FROM mart_data_quality_summary").fetchone()[0]

    conn.execute("""
    INSERT INTO command_center_overview_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (cc_active_headcount, cc_payroll_cost, cc_attendance_compliance_pct, cc_saudization_pct, cc_open_er_cases, cc_open_requisitions, cc_review_completion_pct, cc_total_active_exceptions, cc_modules_healthy, cc_last_data_refresh, cc_latest_source_business_date, cc_data_quality_score))

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_overview AS
    SELECT * FROM command_center_overview_data;
    """)
    print("Created table-backed view 'mart_command_center_overview'")


    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_priority_alerts AS
    SELECT 
        module_key || '_' || issue_type AS alert_id,
        module_key,
        module_label,
        severity,
        issue_type,
        COUNT(*) AS issue_count,
        MAX(recommended_action) AS recommended_action,
        MAX(source_mart) AS source_mart,
        MAX(route_path) AS route_path
    FROM base_command_center_exception_sources
    GROUP BY module_key, module_label, severity, issue_type
    ORDER BY CASE WHEN severity = 'Critical' THEN 1 ELSE 2 END ASC, issue_count DESC;
    """)
    print("Created view 'mart_command_center_priority_alerts'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_exception_summary AS
    SELECT 
        module_key,
        module_label,
        severity,
        issue_type,
        COUNT(*) AS exception_count,
        MAX(recommended_action) AS recommended_action,
        MAX(route_path) AS route_path
    FROM base_command_center_exception_sources
    GROUP BY module_key, module_label, severity, issue_type;
    """)
    print("Created view 'mart_command_center_exception_summary'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_navigation_status AS
    SELECT module_key, page_key, route_path, 'Registered' AS status FROM base_command_center_module_registry;
    """)
    print("Created view 'mart_command_center_navigation_status'")

    conn.execute("""
    CREATE OR REPLACE VIEW mart_command_center_filter_options AS
    SELECT 
        (SELECT report_month FROM base_command_center_report_context) AS report_month,
        ARRAY(SELECT DISTINCT company FROM employees WHERE company IS NOT NULL) AS companies,
        ARRAY(SELECT DISTINCT project FROM employees WHERE project IS NOT NULL) AS projects,
        ARRAY(SELECT DISTINCT department FROM employees WHERE department IS NOT NULL) AS departments,
        ARRAY(SELECT DISTINCT cost_center FROM employees WHERE cost_center IS NOT NULL) AS cost_centers,
        CAST([] AS VARCHAR[]) AS locations,
        ARRAY(SELECT DISTINCT nationality FROM employees WHERE nationality IS NOT NULL) AS nationalities,
        ARRAY(SELECT DISTINCT module_key FROM base_command_center_module_registry) AS modules;
    """)
    print("Created view 'mart_command_center_filter_options'")

    # Run Command Center database reconciliation checks
    try:
        print("Running Command Center integration reconciliation checks...")
        
        # 1. Active Headcount
        kpi_hc = conn.execute("SELECT active_headcount FROM mart_command_center_overview").fetchone()[0]
        ref_hc = conn.execute("SELECT active_headcount FROM mart_workforce_kpis").fetchone()[0]
        if kpi_hc != ref_hc:
            raise ValueError(f"Command Center Active Headcount ({kpi_hc}) != Workforce Active Headcount ({ref_hc})")

        # 2. Payroll Cost
        kpi_pay = conn.execute("SELECT payroll_cost FROM mart_command_center_overview").fetchone()[0]
        ref_pay = conn.execute("SELECT total_payroll_cost FROM mart_payroll_kpis").fetchone()[0]
        if abs(kpi_pay - ref_pay) > 0.01:
            raise ValueError(f"Command Center Payroll Cost ({kpi_pay}) != Payroll Cost ({ref_pay})")

        # 3. Attendance Compliance
        kpi_att = conn.execute("SELECT attendance_compliance_pct FROM mart_command_center_overview").fetchone()[0]
        ref_att = conn.execute("SELECT attendance_compliance_pct FROM mart_attendance_kpis").fetchone()[0]
        if abs(kpi_att - ref_att) > 0.001:
            raise ValueError(f"Command Center Attendance Compliance ({kpi_att}) != Attendance Compliance ({ref_att})")

        # 4. Saudization %
        kpi_saudi = conn.execute("SELECT saudization_pct FROM mart_command_center_overview").fetchone()[0]
        ref_saudi = conn.execute("SELECT saudization_pct FROM mart_compliance_kpis").fetchone()[0]
        if abs(kpi_saudi - ref_saudi) > 0.001:
            raise ValueError(f"Command Center Saudization ({kpi_saudi}) != Compliance Saudization ({ref_saudi})")

        # 5. Open ER Cases
        kpi_er = conn.execute("SELECT open_er_cases FROM mart_command_center_overview").fetchone()[0]
        ref_er = conn.execute("SELECT total_open_er_cases FROM mart_er_kpis").fetchone()[0]
        if kpi_er != ref_er:
            raise ValueError(f"Command Center Open ER Cases ({kpi_er}) != ER Open Cases ({ref_er})")

        # 6. Open Requisitions
        kpi_req = conn.execute("SELECT open_requisitions FROM mart_command_center_overview").fetchone()[0]
        ref_req = conn.execute("SELECT open_requisitions FROM mart_recruitment_kpis").fetchone()[0]
        if kpi_req != ref_req:
            raise ValueError(f"Command Center Open Requisitions ({kpi_req}) != Recruitment Open Requisitions ({ref_req})")

        # 7. Review Completion %
        kpi_talent = conn.execute("SELECT review_completion_pct FROM mart_command_center_overview").fetchone()[0]
        ref_talent = conn.execute("SELECT review_completion_pct FROM mart_talent_kpis").fetchone()[0]
        if abs(kpi_talent - ref_talent) > 0.001:
            raise ValueError(f"Command Center Review Completion ({kpi_talent}) != Talent Review Completion ({ref_talent})")

        # 8. Total Active Exceptions
        kpi_exc = conn.execute("SELECT total_active_exceptions FROM mart_command_center_overview").fetchone()[0]
        actual_exc = conn.execute("SELECT COUNT(*) FROM base_command_center_exception_sources").fetchone()[0]
        if kpi_exc != actual_exc:
            raise ValueError(f"Command Center Total Active Exceptions ({kpi_exc}) != actual combined exceptions ({actual_exc})")

        # 9. Modules registry count = 9
        reg_count = conn.execute("SELECT COUNT(*) FROM base_command_center_module_registry").fetchone()[0]
        if reg_count != 9:
            raise ValueError(f"Command Center Module registry count ({reg_count}) != 9")

        # 10. Data freshness rows = 9
        fresh_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_data_freshness").fetchone()[0]
        if fresh_count != 9:
            raise ValueError(f"Command Center Freshness rows count ({fresh_count}) != 9")

        # 11. Navigation status rows = 9
        nav_count = conn.execute("SELECT COUNT(*) FROM mart_command_center_navigation_status").fetchone()[0]
        if nav_count != 9:
            raise ValueError(f"Command Center Navigation status rows count ({nav_count}) != 9")

        print("Command Center integration reconciliation checks PASSED.")
    except Exception as e:
        print(f"Command Center reconciliation check FAILED: {str(e)}")
        raise e

    # Close connection
    conn.close()
    print("DuckDB database warehouse creation complete.")




if __name__ == "__main__":
    build_warehouse()

