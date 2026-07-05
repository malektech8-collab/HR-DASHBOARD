{{ config(materialized='view') }}

-- 1. Missing check-in
    SELECT 
        employee_id,
        employee_name,
        'Missing Check-in' AS issue_type,
        'Employee has actual check-out but actual check-in is missing on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Request employee to provide check-in time' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE actual_check_in IS NULL AND actual_check_out IS NOT NULL

    UNION ALL

    -- 2. Missing check-out
    SELECT 
        employee_id,
        employee_name,
        'Missing Check-out' AS issue_type,
        'Employee has actual check-in but actual check-out is missing on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Request employee to provide check-out time' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE actual_check_in IS NOT NULL AND actual_check_out IS NULL

    UNION ALL

    -- 3. Both punches missing
    SELECT 
        employee_id,
        employee_name,
        'Both Punches Missing' AS issue_type,
        'Expected workday on ' || strftime(calendar_date, '%Y-%m-%d') || ' has both check-in and check-out missing but absence days is 0' AS description,
        'Warning' AS severity,
        'Record absence or collect punch times' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE actual_check_in IS NULL AND actual_check_out IS NULL AND absence_days = 0

    UNION ALL

    -- 4. One punch only
    SELECT 
        employee_id,
        employee_name,
        'One Punch Only' AS issue_type,
        'Only one punch recorded on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Reconcile check-in or check-out time' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE (actual_check_in IS NULL AND actual_check_out IS NOT NULL) 
       OR (actual_check_in IS NOT NULL AND actual_check_out IS NULL)

    UNION ALL

    -- 5. Late arrival without excuse
    SELECT 
        employee_id,
        employee_name,
        'Late Arrival Without Excuse' AS issue_type,
        'Employee arrived late by ' || calculated_late_minutes || ' minutes on ' || strftime(calendar_date, '%Y-%m-%d') || ' without an excuse' AS description,
        'Warning' AS severity,
        'Follow up with manager for excuse authorization' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE calculated_late_minutes > 0 AND (excused_late_minutes IS NULL OR excused_late_minutes = 0)

    UNION ALL

    -- 6. Excused late minutes greater than actual late minutes
    SELECT 
        employee_id,
        employee_name,
        'Excused Late Exceeds Actual' AS issue_type,
        'Excused late minutes (' || excused_late_minutes || ') exceeds actual late minutes (' || calculated_late_minutes || ') on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Review and adjust excused late minutes' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE excused_late_minutes > calculated_late_minutes

    UNION ALL

    -- 7. Source late minutes mismatch
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Source Late Minutes Mismatch' AS issue_type,
        'Source late minutes (' || COALESCE(late_minutes, 0) || ') does not match calculated (' || calculated_late_minutes || ') on ' || strftime(attendance_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Verify source system lateness logic and parameters' AS recommended_action
    FROM {{ ref('base_attendance_current') }}
    WHERE COALESCE(late_minutes, 0) != calculated_late_minutes

    UNION ALL

    -- 8. Source net late minutes mismatch
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Source Net Late Minutes Mismatch' AS issue_type,
        'Source net late minutes (' || COALESCE(net_late_minutes, 0) || ') does not match calculated (' || calculated_net_late_minutes || ') on ' || strftime(attendance_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Verify source system net lateness calculations' AS recommended_action
    FROM {{ ref('base_attendance_current') }}
    WHERE COALESCE(net_late_minutes, 0) != calculated_net_late_minutes

    UNION ALL

    -- 9. Overtime hours without {{ ref('stg_payroll') }} overtime amount
    SELECT 
        employee_id,
        employee_name,
        'Overtime Amount Missing' AS issue_type,
        'Employee has approved overtime hours (' || attendance_ot_hours || ') but {{ ref('stg_payroll') }} overtime amount is zero' AS description,
        'Critical' AS severity,
        'Process overtime payment in monthly {{ ref('stg_payroll') }}' AS recommended_action
    FROM {{ ref('base_attendance_payroll_overtime') }}
    WHERE attendance_ot_hours > 0 AND payroll_ot_cost = 0

    UNION ALL

    -- 10. Payroll overtime amount without {{ ref('stg_attendance') }} overtime hours
    SELECT 
        employee_id,
        employee_name,
        'Overtime Hours Missing' AS issue_type,
        'Employee has {{ ref('stg_payroll') }} overtime payment (' || payroll_ot_cost || ' SAR) but approved overtime hours are zero' AS description,
        'Critical' AS severity,
        'Investigate overtime validation or manual entry error' AS recommended_action
    FROM {{ ref('base_attendance_payroll_overtime') }}
    WHERE payroll_ot_cost > 0 AND attendance_ot_hours = 0

    UNION ALL

    -- 11. Attendance record for inactive employee
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Attendance for Inactive Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is inactive' AS description,
        'Critical' AS severity,
        'Verify employee work status and {{ ref('stg_attendance') }} logs' AS recommended_action
    FROM {{ ref('base_attendance_current') }}
    WHERE emp_status = 'Inactive'

    UNION ALL

    -- 12. Attendance record for terminated employee
    SELECT 
        employee_id,
        emp_name AS employee_name,
        'Attendance for Terminated Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is terminated' AS description,
        'Critical' AS severity,
        'Deactivate employee security badge and delete profile' AS recommended_action
    FROM {{ ref('base_attendance_current') }}
    WHERE emp_status = 'Terminated'

    UNION ALL

    -- 13. Attendance record for unknown employee
    SELECT 
        employee_id,
        'Unknown Employee' AS employee_name,
        'Attendance for Unknown Employee' AS issue_type,
        'Attendance record exists on ' || strftime(attendance_date, '%Y-%m-%d') || ' but employee is not found in master records' AS description,
        'Critical' AS severity,
        'Register employee in master file or verify employee ID' AS recommended_action
    FROM {{ ref('base_attendance_current') }}
    WHERE record_classification = 'Unknown employee {{ ref('stg_attendance') }}'

    UNION ALL

    -- 14. Active employee missing {{ ref('stg_attendance') }} record for expected workday
    SELECT 
        employee_id,
        employee_name,
        'Missing Workday Attendance' AS issue_type,
        'Active employee has no {{ ref('stg_attendance') }} record for expected workday on ' || strftime(calendar_date, '%Y-%m-%d') AS description,
        'Warning' AS severity,
        'Confirm if employee was absent, on leave, or missed punch' AS recommended_action
    FROM {{ ref('base_expected_attendance') }}
    WHERE attendance_date IS NULL
