{{ config(materialized='view') }}

SELECT 
        p.*,
        COALESCE(e.project, 'Missing Project') AS emp_project,
        COALESCE(e.department, 'Missing Department') AS emp_department,
        -- NO COALESCE. A sentinel renders an absence as a value: a client with
        -- no cost-centre column would get a payroll breakdown bucketed under a
        -- category literally named 'Missing Cost Center', which is the
        -- COALESCE(project, 'Unassigned') defect in a second place. The NULL is
        -- kept, and mart_payroll_exceptions tests for it directly.
        e.cost_center AS emp_cost_center,
        COALESCE(e.status, 'Inactive/Terminated/Unknown') AS emp_status,
        e.employee_name,
        e.is_saudi
    FROM {{ ref('stg_payroll') }} p
    LEFT JOIN {{ ref('base_active_workforce') }} e ON p.employee_id = e.employee_id
    WHERE p.payroll_period = '{{ var('report_month') }}'
