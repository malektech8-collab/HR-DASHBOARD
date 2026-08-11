{{ config(materialized='view') }}

SELECT 
    COALESCE(a.project, 'Missing Project') AS project,
    COUNT(DISTINCT a.employee_id) AS headcount,
    CASE 
        WHEN COUNT(a.absence_days) = 0 THEN NULL
        ELSE 1.0 - (COUNT(CASE WHEN a.calculated_net_late_minutes > 0 OR a.missing_punch_count > 0 OR a.absence_days > 0 THEN 1 END) / CAST(COUNT(a.absence_days) AS DOUBLE))
    END AS attendance_compliance_pct,
    SUM(a.absence_days) AS absence_days,
    COALESCE(SUM(a.calculated_late_minutes), 0) AS late_minutes,
    COALESCE(SUM(a.missing_punch_count), 0) AS missing_punches,
    COALESCE(SUM(CASE WHEN a.overtime_approved = TRUE THEN a.overtime_hours ELSE 0.0 END), 0.0) AS overtime_hours,
    COALESCE((
        SELECT SUM(b.payroll_ot_cost) 
        FROM {{ ref('base_attendance_payroll_overtime') }} b 
        WHERE b.project = a.project
    ), 0.0) AS overtime_cost
FROM {{ ref('base_expected_attendance') }} a
GROUP BY a.project
