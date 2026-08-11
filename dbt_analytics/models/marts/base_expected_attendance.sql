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
        -- Category F. Inside declared coverage a missing row IS an absence,
        -- and that inference is the whole point of the model. Outside it, a
        -- missing row means the client has not sent us that day.
        --
        -- NULL, not 1.0 (a fabricated absence, and in KSA absence records feed
        -- Article 80 dismissal grounds and payroll deduction) and not 0.0
        -- either: 0.0 asserts the employee was PRESENT, it is silent where a
        -- fabricated absence at least raises an exception, and it pushes
        -- attendance_compliance_pct toward 100% exactly when the data is
        -- thinnest. NULL says "not measured", and SUM/COUNT/AVG then skip it
        -- without a single special case.
        CASE
            WHEN ed.calendar_date < DATE '{{ var('attendance_coverage_start') }}'
              OR ed.calendar_date > DATE '{{ var('attendance_coverage_end') }}'
                THEN NULL
            WHEN att.employee_id IS NULL THEN 1.0
            ELSE COALESCE(att.absence_days, 0.0)
        END AS absence_days,
        -- The row stays either way, so the gap is COUNTABLE. Narrowing the
        -- calendar instead would show a shorter month with no indication that
        -- anything was missing.
        CASE
            WHEN ed.calendar_date BETWEEN DATE '{{ var('attendance_coverage_start') }}'
                                      AND DATE '{{ var('attendance_coverage_end') }}'
                THEN 'covered'
            ELSE 'not_reported'
        END AS coverage_status
    FROM employee_dates ed
    LEFT JOIN {{ ref('base_attendance_current') }} att 
      ON ed.employee_id = att.employee_id 
     AND ed.calendar_date = att.attendance_date
