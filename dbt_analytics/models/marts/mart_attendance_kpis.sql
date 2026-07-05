{{ config(materialized='view') }}

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
        (SELECT COALESCE(SUM(payroll_ot_cost), 0.0) FROM {{ ref('base_attendance_payroll_overtime') }}) AS overtime_cost,
        (SELECT COUNT(*) FROM {{ ref('mart_attendance_exceptions') }}) AS attendance_exception_count
    FROM {{ ref('base_expected_attendance') }}
