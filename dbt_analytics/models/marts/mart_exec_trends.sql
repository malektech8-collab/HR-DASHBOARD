{{ config(materialized='view') }}

WITH payroll_months AS (
        SELECT 
            payroll_period AS month,
            SUM(gross_pay) AS payroll_cost
        FROM {{ ref('stg_payroll') }}
        GROUP BY payroll_period
    ),
    headcount_months AS (
        -- Historical anchors: report_month minus 2 and minus 1, derived in build_warehouse.py (step 2a.5).
        SELECT
            '{{ var('trend_m1') }}' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE joining_date <= '{{ var('trend_m1_end') }}'
          AND (termination_date IS NULL OR termination_date > '{{ var('trend_m1_end') }}')
        UNION ALL
        SELECT
            '{{ var('trend_m2') }}' AS month,
            COUNT(DISTINCT employee_id) AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE joining_date <= '{{ var('trend_m2_end') }}'
          AND (termination_date IS NULL OR termination_date > '{{ var('trend_m2_end') }}')
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
