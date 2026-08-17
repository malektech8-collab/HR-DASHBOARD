{{ config(materialized='view') }}

SELECT 
        payroll_period AS month,
        COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
        COALESCE(SUM(basic_salary), 0.0) AS basic_salary,
        COALESCE(SUM(housing_allowance + transport_allowance
                         + COALESCE(other_allowances, 0.0)), 0.0) AS allowances,
        CASE WHEN {{ var('has_payroll_overtime_sql') }}
             THEN COALESCE(SUM(overtime_amount), 0.0) END AS overtime,
        CASE WHEN {{ var('has_payroll_deductions_sql') }}
             THEN COALESCE(SUM(deductions), 0.0) END AS deductions,
        COALESCE(SUM(net_pay), 0.0) AS net_payroll,
        COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('stg_payroll') }}
    GROUP BY payroll_period
    ORDER BY payroll_period
