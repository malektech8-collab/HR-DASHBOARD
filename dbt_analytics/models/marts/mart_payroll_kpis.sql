{{ config(materialized='view') }}

WITH curr AS (
        SELECT 
            COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost,
            COALESCE(SUM(basic_salary), 0.0) AS basic_salary_cost,
            COALESCE(SUM(housing_allowance + transport_allowance + other_allowances), 0.0) AS allowances_cost,
            COALESCE(SUM(overtime_amount), 0.0) AS overtime_cost,
            COALESCE(SUM(deductions), 0.0) AS deductions,
            COALESCE(SUM(net_pay), 0.0) AS net_payroll,
            COUNT(DISTINCT employee_id) AS employees_paid
        FROM {{ ref('base_payroll_current') }}
    ),
    prev AS (
        SELECT COALESCE(SUM(gross_pay), 0.0) AS total_payroll_cost
        FROM {{ ref('base_payroll_previous') }}
    )
    SELECT 
        curr.total_payroll_cost,
        curr.basic_salary_cost,
        curr.allowances_cost,
        curr.overtime_cost,
        curr.deductions,
        curr.net_payroll,
        CASE WHEN curr.employees_paid = 0 THEN 0.0 ELSE curr.total_payroll_cost / curr.employees_paid END AS avg_cost_per_employee,
        CASE 
            WHEN COALESCE(prev.total_payroll_cost, 0.0) = 0.0 THEN 0.0 
            ELSE (curr.total_payroll_cost - prev.total_payroll_cost) / prev.total_payroll_cost 
        END AS payroll_variance_pct,
        curr.employees_paid,
        (SELECT COUNT(*) FROM {{ ref('mart_payroll_exceptions') }}) AS payroll_exception_count
    FROM curr, prev
