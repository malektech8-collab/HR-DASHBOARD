{{ config(materialized='view') }}

WITH anchor AS (
        SELECT 
            CAST('{{ var('report_month') }}-01' AS DATE) AS month_start,
            last_day(CAST('{{ var('report_month') }}-01' AS DATE)) AS month_end
    ),
    att_ot AS (
        SELECT employee_id, COALESCE(SUM(overtime_hours), 0.0) AS ot_hours
        FROM {{ ref('stg_attendance') }}, anchor
        WHERE attendance_date BETWEEN month_start AND month_end
        GROUP BY employee_id
    )
    -- 1. Inactive employee with payroll record
    SELECT 
        p.employee_id, COALESCE(p.employee_name, 'Unknown Employee') AS employee_name, 
        'Inactive Employee Payroll' AS issue_type,
        'Employee has status ' || p.emp_status || ' but appeared in active payroll run' AS description,
        'Critical' AS severity, 'Hold payroll and verify termination status' AS recommended_action
    FROM {{ ref('base_payroll_current') }} p
    WHERE p.emp_status = 'Inactive/Terminated/Unknown'
    UNION ALL
    -- 2. Active employee missing payroll record
    SELECT 
        e.employee_id, e.employee_name, 'Active Employee Missing Payroll' AS issue_type,
        'Active employee has no payroll record for current period' AS description,
        'Critical' AS severity, 'Check payroll run for missing record' AS recommended_action
    FROM {{ ref('base_active_workforce') }} e
    LEFT JOIN {{ ref('base_payroll_current') }} p ON e.employee_id = p.employee_id
    WHERE p.employee_id IS NULL
    UNION ALL
    -- 3. Negative gross pay
    SELECT 
        employee_id, employee_name, 'Negative Gross Pay' AS issue_type,
        'Employee has negative gross pay: ' || CAST(gross_pay AS VARCHAR) AS description,
        'Critical' AS severity, 'Correct payroll calculation' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE gross_pay < 0
    UNION ALL
    -- 4. Negative net pay
    SELECT 
        employee_id, employee_name, 'Negative Net Pay' AS issue_type,
        'Employee has negative net pay: ' || CAST(net_pay AS VARCHAR) AS description,
        'Critical' AS severity, 'Correct payroll deductions' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE net_pay < 0
    UNION ALL
    -- 5. Net pay greater than gross pay
    SELECT 
        employee_id, employee_name, 'Net Pay Exceeds Gross Pay' AS issue_type,
        'Net pay (' || CAST(net_pay AS VARCHAR) || ') exceeds gross pay (' || CAST(gross_pay AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Review deduction/tax calculations' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE net_pay > gross_pay
    UNION ALL
    -- 6. Missing cost center
    SELECT 
        employee_id, employee_name, 'Missing Cost Center' AS issue_type,
        'Payroll record is missing a cost center code' AS description,
        'Warning' AS severity, 'Assign cost center in profile' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    -- Scoped to clients who PROVIDE the column. `emp_cost_center` no longer
    -- carries a 'Missing Cost Center' sentinel - base_payroll_current keeps the
    -- NULL, because a sentinel renders an absence as a value.
    WHERE {{ var('has_cost_center_source_sql') }}
      AND (cost_center IS NULL OR cost_center = '' OR emp_cost_center IS NULL)
    UNION ALL
    -- 7. Missing project
    SELECT 
        employee_id, employee_name, 'Missing Project' AS issue_type,
        'Payroll record is missing a project assignment' AS description,
        'Warning' AS severity, 'Assign project to employee' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE project IS NULL OR project = '' OR emp_project = 'Missing Project'
    UNION ALL
    -- 8. Overtime cost without overtime hours
    SELECT 
        p.employee_id, p.employee_name, 'Overtime Cost Without Hours' AS issue_type,
        'Employee paid overtime (' || CAST(p.overtime_amount AS VARCHAR) || ') but has 0 overtime hours in attendance' AS description,
        'Warning' AS severity, 'Verify attendance punches and overtime logs' AS recommended_action
    FROM {{ ref('base_payroll_current') }} p
    LEFT JOIN att_ot o ON p.employee_id = o.employee_id
    WHERE p.overtime_amount > 0 AND (o.ot_hours IS NULL OR o.ot_hours = 0)
    UNION ALL
    -- 9. Large payroll variance vs previous month
    SELECT 
        c.employee_id, c.employee_name, 'Large Payroll Variance' AS issue_type,
        'Employee gross pay changed by ' || CAST(c.gross_pay - p.gross_pay AS VARCHAR) || ' SAR vs last month (Basic salary change: ' || CAST(ROUND(ABS(c.basic_salary - p.basic_salary)/NULLIF(p.basic_salary, 0)*100, 2) AS VARCHAR) || '%)' AS description,
        'Warning' AS severity, 'Review contract salary history for updates' AS recommended_action
    FROM {{ ref('base_payroll_current') }} c
    JOIN {{ ref('base_payroll_previous') }} p ON c.employee_id = p.employee_id
    WHERE ABS(c.gross_pay - p.gross_pay) > 2000 
       OR (p.basic_salary > 0 AND ABS(c.basic_salary - p.basic_salary) / p.basic_salary > 0.10)
    UNION ALL
    -- 10. Duplicate payroll record for same employee and period
    SELECT 
        p.employee_id, COALESCE(e.employee_name, 'Unknown Employee') AS employee_name, 'Duplicate Payroll Record' AS issue_type,
        'Multiple payroll records found for employee ' || p.employee_id || ' in period ' || p.payroll_period AS description,
        'Critical' AS severity, 'Remove duplicate payroll line' AS recommended_action
    FROM {{ ref('stg_payroll') }} p
    LEFT JOIN {{ ref('base_active_workforce') }} e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = '{{ var('report_month') }}'
    GROUP BY p.employee_id, p.payroll_period, e.employee_name
    HAVING COUNT(*) > 1
    UNION ALL
    -- 11. Payroll component mismatch
    SELECT 
        employee_id, employee_name, 'Payroll Component Mismatch' AS issue_type,
        'Gross pay (' || CAST(gross_pay AS VARCHAR) || ') does not equal sum of components (' || CAST(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Recalculate gross salary components' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE ABS(gross_pay - (basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount)) > 0.01
    UNION ALL
    -- 12. Net pay mismatch
    SELECT 
        employee_id, employee_name, 'Net Pay Mismatch' AS issue_type,
        'Net pay (' || CAST(net_pay AS VARCHAR) || ') does not equal gross minus deductions (' || CAST(gross_pay - deductions AS VARCHAR) || ')' AS description,
        'Critical' AS severity, 'Check deduction sums and tax deductions' AS recommended_action
    FROM {{ ref('base_payroll_current') }}
    WHERE ABS(net_pay - (gross_pay - deductions)) > 0.01
