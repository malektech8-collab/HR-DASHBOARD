{{ config(materialized='view') }}

WITH curr AS (
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
    ),
    prev AS (
        SELECT 
            'Basic Salary' AS component, COALESCE(SUM(basic_salary), 0.0) AS amount FROM {{ ref('base_payroll_previous') }}
        UNION ALL
        SELECT 
            'Housing Allowance' AS component, COALESCE(SUM(housing_allowance), 0.0) AS amount FROM {{ ref('base_payroll_previous') }}
        UNION ALL
        SELECT 
            'Transport Allowance' AS component, COALESCE(SUM(transport_allowance), 0.0) AS amount FROM {{ ref('base_payroll_previous') }}
        UNION ALL
        SELECT 
            'Other Allowances' AS component, CASE WHEN {{ var('has_payroll_other_allowances_sql') }}
             THEN COALESCE(SUM(other_allowances), 0.0) END AS amount FROM {{ ref('base_payroll_previous') }}
        UNION ALL
        SELECT 
            'Overtime' AS component, CASE WHEN {{ var('has_payroll_overtime_sql') }}
             THEN COALESCE(SUM(overtime_amount), 0.0) END AS amount FROM {{ ref('base_payroll_previous') }}
        UNION ALL
        SELECT 
            'Deductions' AS component, CASE WHEN {{ var('has_payroll_deductions_sql') }}
             THEN COALESCE(SUM(deductions), 0.0) END AS amount FROM {{ ref('base_payroll_previous') }}
    )
    SELECT 
        curr.component,
        COALESCE(prev.amount, 0.0) AS prev_amount,
        curr.amount AS curr_amount,
        curr.amount - COALESCE(prev.amount, 0.0) AS change_amount,
        CASE 
            WHEN COALESCE(prev.amount, 0.0) = 0.0 THEN 0.0 
            ELSE (curr.amount - prev.amount) / prev.amount 
        END AS change_pct
    FROM curr
    LEFT JOIN prev ON curr.component = prev.component
