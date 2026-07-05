{{ config(materialized='view') }}

WITH calendar_dates AS (
        SELECT CAST(range AS DATE) AS calendar_date
        FROM range(
            CAST(DATE '{{ var('start_date_str') }}' AS TIMESTAMP),
            CAST(DATE '{{ var('end_date_str') }}' + INTERVAL 1 DAY AS TIMESTAMP),
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
        CROSS JOIN {{ ref('base_employees_deduplicated') }} e
        WHERE e.status = 'Active' 
          AND c.calendar_date >= e.joining_date 
          AND (e.termination_date IS NULL OR c.calendar_date <= e.termination_date)
          AND dayname(c.calendar_date) NOT IN ({{ var('weekend_days_sql') }})
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
    LEFT JOIN {{ ref('base_attendance_current') }} att 
      ON ed.employee_id = att.employee_id 
     AND ed.calendar_date = att.attendance_date
