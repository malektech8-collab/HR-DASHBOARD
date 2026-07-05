{{ config(materialized='view') }}

-- Sample-mode simulated history (clearly documented as mock trend history)
    SELECT '2026-04' AS period, 8 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 44.44 AS saudization_pct
    UNION ALL
    SELECT '2026-05' AS period, 9 AS saudi_headcount, 10 AS non_saudi_headcount, 0 AS employees_missing_nationality, 47.37 AS saudization_pct
    UNION ALL
    -- Live dynamic data
    SELECT '{{ var('report_month') }}' AS period, saudi_headcount, non_saudi_headcount, employees_missing_nationality, saudization_pct FROM {{ ref('mart_compliance_kpis') }}
