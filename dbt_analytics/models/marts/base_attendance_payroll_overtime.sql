{{ config(materialized='view') }}

WITH att_ot AS (
        SELECT 
            employee_id,
            SUM(overtime_hours) AS attendance_ot_hours
        FROM {{ ref('base_attendance_current') }}
        WHERE overtime_approved = TRUE
        GROUP BY employee_id
    ),
    pay_ot AS (
        SELECT 
            employee_id,
            overtime_amount AS payroll_ot_cost
        FROM {{ ref('base_payroll_current') }}
    )
    SELECT 
        COALESCE(att_ot.employee_id, pay_ot.employee_id) AS employee_id,
        e.employee_name,
        e.department,
        e.project,
        COALESCE(att_ot.attendance_ot_hours, 0.0) AS attendance_ot_hours,
        COALESCE(pay_ot.payroll_ot_cost, 0.0) AS payroll_ot_cost,
        CASE 
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) > 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) > 0.0 THEN 'Reconciled'
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) > 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) = 0.0 THEN 'OT in Attendance only'
            WHEN COALESCE(att_ot.attendance_ot_hours, 0.0) = 0.0 AND COALESCE(pay_ot.payroll_ot_cost, 0.0) > 0.0 THEN 'OT in Payroll only'
            ELSE 'No Overtime'
        END AS reconciliation_status
    FROM att_ot
    FULL OUTER JOIN pay_ot ON att_ot.employee_id = pay_ot.employee_id
    LEFT JOIN {{ ref('base_employees_deduplicated') }} e ON COALESCE(att_ot.employee_id, pay_ot.employee_id) = e.employee_id
