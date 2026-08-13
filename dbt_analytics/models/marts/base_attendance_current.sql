{{ config(materialized='view') }}

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
                GREATEST(date_diff('minute', a.scheduled_start, a.actual_check_in) - {{ var('grace_period_minutes') }}, 0)
            ELSE 0
        END AS calculated_late_minutes,
        -- Net late minutes
        GREATEST(
            CASE 
                WHEN a.actual_check_in IS NOT NULL AND a.scheduled_start IS NOT NULL THEN
                    GREATEST(date_diff('minute', a.scheduled_start, a.actual_check_in) - {{ var('grace_period_minutes') }}, 0)
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
    FROM {{ ref('stg_attendance') }} a
    LEFT JOIN {{ ref('base_employees_deduplicated') }} e ON a.employee_id = e.employee_id
    WHERE a.attendance_date BETWEEN DATE '{{ var('start_date_str') }}' AND DATE '{{ var('end_date_str') }}'
