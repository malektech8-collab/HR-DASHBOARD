{{ config(materialized='view') }}

WITH payroll_months AS (
        SELECT 
            payroll_period AS month,
            SUM(gross_pay) AS payroll_cost
        FROM {{ ref('stg_payroll') }}
        GROUP BY payroll_period
    ),
    headcount_months AS (
        -- Ruling 2, as amended. Point-in-time headcount from client-provided
        -- joining/termination dates is legitimate DERIVATION, not fabrication --
        -- but only where the file reaches back far enough to contain the people
        -- who have since left. An active-only master understates each past month
        -- by exactly those leavers, so a flat or shrinking company renders as
        -- smooth growth: a false story that looks credible. So a month ending
        -- before the DECLARED history depth is NULL, never a derived figure.
        -- Historical anchors: report_month minus 2 and minus 1, derived in build_warehouse.py (step 2a.5).
        SELECT
            '{{ var('trend_m1') }}' AS month,
            CASE WHEN DATE '{{ var('trend_m1_end') }}' < DATE '{{ var('employees_history_since') }}'
                 THEN NULL
                 ELSE COUNT(DISTINCT employee_id) END AS active_headcount
        FROM {{ ref('stg_employees') }}
        WHERE joining_date <= '{{ var('trend_m1_end') }}'
          AND (termination_date IS NULL OR termination_date > '{{ var('trend_m1_end') }}')
        UNION ALL
        SELECT
            '{{ var('trend_m2') }}' AS month,
            CASE WHEN DATE '{{ var('trend_m2_end') }}' < DATE '{{ var('employees_history_since') }}'
                 THEN NULL
                 ELSE COUNT(DISTINCT employee_id) END AS active_headcount
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
        -- Ruling 1. A month with no payroll is NULL, not 0.0: three points
        -- with gaps, never a chart that says the client paid nobody. This
        -- COALESCE was the Category F finding; do not restore it.
        pm.payroll_cost AS payroll_cost
    FROM headcount_months hm
    LEFT JOIN payroll_months pm ON hm.month = pm.month
    ORDER BY hm.month
