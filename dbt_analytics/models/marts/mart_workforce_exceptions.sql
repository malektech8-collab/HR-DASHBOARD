{{ config(materialized='view') }}

WITH anchor AS (
        SELECT last_day(CAST('{{ var('report_month') }}-01' AS DATE)) AS anchor_date
    )
    -- 1. Missing Manager
    SELECT 
        employee_id, employee_name, 'Missing Manager' AS issue_type,
        'Active employee is missing a manager ID' AS description, 'Warning' AS severity,
        'Assign supervisor/manager in employee profile' AS recommended_action
    FROM {{ ref('base_active_workforce') }}
    WHERE manager_id IS NULL OR manager_id = ''
    UNION ALL
    -- 2. Missing Project
    SELECT 
        employee_id, employee_name, 'Missing Project' AS issue_type,
        'Active employee is missing a project code' AS description, 'Warning' AS severity,
        'Assign cost project code in master profile' AS recommended_action
    FROM {{ ref('base_active_workforce') }}
    WHERE project IS NULL OR project = ''
    UNION ALL
    -- 3. Missing Cost Center
    SELECT 
        employee_id, employee_name, 'Missing Cost Center' AS issue_type,
        'Active employee is missing a cost center' AS description, 'Warning' AS severity,
        'Assign financial cost center code in master profile' AS recommended_action
    FROM {{ ref('base_active_workforce') }}
    WHERE cost_center IS NULL OR cost_center = ''
    UNION ALL
    -- 4. Missing Nationality
    SELECT 
        employee_id, employee_name, 'Missing Nationality' AS issue_type,
        'Employee nationality field is empty' AS description, 'Warning' AS severity,
        'Update nationality field in employee record' AS recommended_action
    FROM {{ ref('stg_employees') }}
    WHERE nationality IS NULL OR nationality = ''
    UNION ALL
    -- 5. Duplicate Employee ID
    SELECT 
        employee_id, employee_name, 'Duplicate Employee ID' AS issue_type,
        'Employee ID is duplicated in master log' AS description, 'Critical' AS severity,
        'Merge or delete duplicate employee record in ERP' AS recommended_action
    FROM {{ ref('stg_employees') }}
    WHERE employee_id IN (
        SELECT employee_id FROM {{ ref('stg_employees') }} GROUP BY employee_id HAVING COUNT(*) > 1
    )
    UNION ALL
    -- 6. Contract expiring within 30 days
    SELECT 
        employee_id, employee_name, 'Contract Expiry Risk' AS issue_type,
        'Active contract is expiring within 30 days: ' || COALESCE(CAST(contract_end_date AS VARCHAR), 'N/A') AS description, 'Warning' AS severity,
        'Initiate contract renewal in Qiwa' AS recommended_action
    FROM {{ ref('base_active_workforce') }}, anchor
    WHERE contract_end_date BETWEEN anchor_date AND anchor_date + INTERVAL 30 DAY
    UNION ALL
    -- 7. Iqama expiring within 30 days
    SELECT 
        e.employee_id, e.employee_name, 'Iqama Expiry Risk' AS issue_type,
        'Iqama is expiring within 30 days: ' || COALESCE(CAST(c.iqama_expiry AS VARCHAR), 'N/A') AS description, 'Warning' AS severity,
        'Renew Iqama and update labor permit' AS recommended_action
    FROM {{ ref('base_active_workforce') }} e
    JOIN {{ ref('stg_compliance') }} c ON e.employee_id = c.employee_id, anchor
    WHERE e.is_saudi = FALSE AND c.iqama_expiry BETWEEN anchor_date AND anchor_date + INTERVAL 30 DAY
    UNION ALL
    -- 8. Inactive employee appearing in payroll
    SELECT 
        e.employee_id, e.employee_name, 'Inactive Employee Payroll' AS issue_type,
        'Employee status is ' || e.status || ' but appeared in active payroll run' AS description, 'Critical' AS severity,
        'Hold payroll run and check termination status/period logic' AS recommended_action
    FROM {{ ref('stg_payroll') }} p
    JOIN {{ ref('stg_employees') }} e ON p.employee_id = e.employee_id
    WHERE e.status IN ('Inactive', 'Terminated') AND p.payroll_period = '{{ var('report_month') }}'
    UNION ALL
    -- 9. Active employee missing contract end date
    SELECT 
        employee_id, employee_name, 'Missing Contract End Date' AS issue_type,
        'Active employee has no contract end date set' AS description, 'Warning' AS severity,
        'Update contract records with end date' AS recommended_action
    FROM {{ ref('base_active_workforce') }}
    WHERE contract_end_date IS NULL
    UNION ALL
    -- 10. Active employee missing department
    SELECT 
        employee_id, employee_name, 'Missing Department' AS issue_type,
        'Active employee is not assigned to a department' AS description, 'Warning' AS severity,
        'Assign employee to department' AS recommended_action
    FROM {{ ref('base_active_workforce') }}
    WHERE department IS NULL OR department = ''
    UNION ALL
    -- 11. Active non-Saudi employee missing Iqama expiry
    SELECT 
        e.employee_id, e.employee_name, 'Missing Iqama Expiry Date' AS issue_type,
        'Active non-Saudi employee has no Iqama expiry date set' AS description, 'Warning' AS severity,
        'Update compliance records with Iqama expiry date' AS recommended_action
    FROM {{ ref('base_active_workforce') }} e
    LEFT JOIN {{ ref('stg_compliance') }} c ON e.employee_id = c.employee_id
    WHERE e.is_saudi = FALSE AND c.iqama_expiry IS NULL
