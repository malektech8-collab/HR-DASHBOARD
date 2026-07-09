{{ config(materialized='view') }}

WITH payroll_months AS (
        SELECT 
            payroll_period AS month,
            SUM(gross_pay) AS payroll_cost
        FROM {{ ref('stg_payroll') }}
        GROUP BY payroll_period
    ),
    headcount_months AS (
        SELECT 
            '2026-04' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE joining_date <= '2026-04-30' 
          AND (termination_date IS NULL OR termination_date > '2026-04-30')
        UNION ALL
        SELECT 
            '2026-05' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE joining_date <= '2026-05-31' 
          AND (termination_date IS NULL OR termination_date > '2026-05-31')
        UNION ALL
        SELECT
            '{{ var('report_month') }}' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE status = 'Active'
    )
    SELECT 
        hm.month,
        hm.active_headcount,
        COALESCE(pm.payroll_cost, 0.0) AS payroll_cost
    FROM headcount_months hm
    LEFT JOIN payroll_months pm ON hm.month = pm.month
    ORDER BY hm.month
