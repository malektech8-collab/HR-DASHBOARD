{{ config(materialized='view') }}

SELECT 
        p.*,
        COALESCE(e.project, 'Missing Project') AS emp_project,
        COALESCE(e.department, 'Missing Department') AS emp_department,
        COALESCE(e.cost_center, 'Missing Cost Center') AS emp_cost_center,
        COALESCE(e.status, 'Inactive/Terminated/Unknown') AS emp_status,
        e.employee_name,
        e.is_saudi
    FROM {{ ref('stg_payroll') }} p
    LEFT JOIN {{ ref('base_active_workforce') }} e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = strftime(CAST('{{ var('report_month') }}-01' AS DATE) - INTERVAL 1 MONTH, '%Y-%m')
