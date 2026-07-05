{{ config(materialized='view') }}

SELECT 
        emp_department AS department,
        COUNT(DISTINCT employee_id) AS headcount,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost
    FROM {{ ref('base_payroll_current') }}
    GROUP BY emp_department
