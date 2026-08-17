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
        'Other Allowances' AS component, CASE WHEN {{ var('has_payroll_other_allowances_sql') }}
             THEN COALESCE(SUM(other_allowances), 0.0) END AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Overtime' AS component, CASE WHEN {{ var('has_payroll_overtime_sql') }}
             THEN COALESCE(SUM(overtime_amount), 0.0) END AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Deductions' AS component, CASE WHEN {{ var('has_payroll_deductions_sql') }}
             THEN COALESCE(SUM(deductions), 0.0) END AS amount FROM {{ ref('base_payroll_current') }}
    UNION ALL
    SELECT 
        'Unreconciled / Exception Amount' AS component, 
        -- The residual only means anything when every component is present.
        -- Otherwise it silently equals the missing components and would be
        -- read as unexplained payroll.
        CASE WHEN {{ var('has_payroll_other_allowances_sql') }}
              AND {{ var('has_payroll_overtime_sql') }}
             THEN COALESCE(SUM(gross_pay) - SUM(basic_salary + housing_allowance + transport_allowance + other_allowances + overtime_amount), 0.0)
        END AS amount 
    FROM {{ ref('base_payroll_current') }}
