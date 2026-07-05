{{ config(materialized='view') }}

-- Simulated historical trend for MVP visuals
    SELECT '2026-04' AS period, 4 AS new_cases, 3 AS closed_cases
    UNION ALL
    SELECT '2026-05' AS period, 5 AS new_cases, 4 AS closed_cases
    UNION ALL
    -- Live dynamic current period
    SELECT 
        '{er_report_month}' AS period,
        COUNT(CASE WHEN created_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS new_cases,
        COUNT(CASE WHEN closed_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS closed_cases
    FROM {{ ref('base_er_case_population') }}
