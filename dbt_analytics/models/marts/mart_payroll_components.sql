{{ config(materialized='view') }}

SELECT 
        'Basic Salary' AS component, COALESCE(SUM(basic_salary), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Housing Allowance' AS component, COALESCE(SUM(housing_allowance), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Transport Allowance' AS component, COALESCE(SUM(transport_allowance), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Other Allowances' AS component, COALESCE(SUM(other_allowances), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Overtime' AS component, COALESCE(SUM(overtime_amount), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Deductions' AS component, COALESCE(SUM(deductions), 0.0) AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Unreconciled / Exception Amount' AS component, 
        COALESCE(SUM(gross_pay) - SUM(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount), 0.0) AS amount 
    FROM {{ ref('base_payroll_current') }}
