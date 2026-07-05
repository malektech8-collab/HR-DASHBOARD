{{ config(materialized='view') }}

SELECT 
        payroll_period AS month,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(basic_salary), 0.0) AS basic_salary,
        COALESCE(SUM(housing_allowance + transport_allowance + other_allowances), 0.0) AS allowances,
        COALESCE(SUM(overtime_amount), 0.0) AS overtime,
        COALESCE(SUM(deductions), 0.0) AS deductions,
        COALESCE(SUM(net_pay), 0.0) AS net_payroll,
        COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('stg_payroll') }}
    GROUP BY payroll_period
    ORDER BY payroll_period
