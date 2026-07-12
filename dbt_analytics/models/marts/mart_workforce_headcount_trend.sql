{{ config(materialized='view') }}

-- Historical anchors are placeholders; to be replaced by report_month-relative derivation in the resolver cycle (5a).
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
    FROM {{ ref('base_active_workforce') }}
