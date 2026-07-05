{{ config(materialized='view') }}

SELECT 
    COALESCE(a.department, 'Missing Department') AS department,
    COUNT(DISTINCT a.employee_id) AS headcount,
    CASE 
        WHEN COUNT(*) = 0 THEN 1.0
        ELSE 1.0 - (COUNT(CASE WHEN a.calculated_net_late_minutes > 0 OR a.missing_punch_count > 0 OR a.absence_days > 0 THEN 1 END) / CAST(COUNT(*) AS DOUBLE))
    END AS attendance_compliance_pct,
    COALESCE(SUM(a.absence_days), 0.0) AS absence_days,
    COALESCE(SUM(a.calculated_late_minutes), 0) AS late_minutes,
    COALESCE(SUM(a.calculated_net_late_minutes), 0) AS net_late_minutes,
    COALESCE(SUM(a.missing_punch_count), 0) AS missing_punches,
    COALESCE(SUM(CASE WHEN a.overtime_approved = TRUE THEN a.overtime_hours ELSE 0.0 END), 0.0) AS overtime_hours,
    COALESCE((
        SELECT SUM(b.payroll_ot_cost) 
        FROM {{ ref('base_attendance_payroll_overtime') }} b 
        WHERE b.department = a.department
    ), 0.0) AS overtime_cost
FROM {{ ref('base_expected_attendance') }} a
GROUP BY a.department
