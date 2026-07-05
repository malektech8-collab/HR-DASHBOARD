{{ config(materialized='view') }}

SELECT '2026-04' AS period, 12 AS total_reviewed, 10 AS completed_reviews, 85.0 AS completion_pct, 3.6 AS avg_rating
    UNION ALL
    SELECT '2026-05' AS period, 14 AS total_reviewed, 12 AS completed_reviews, 88.0 AS completion_pct, 3.7 AS avg_rating
    UNION ALL
    SELECT '{talent_report_month}' AS period,
        (SELECT COUNT(*) FROM {{ ref('base_talent_employee_population') }}) AS total_reviewed,
        (SELECT COUNT(DISTINCT employee_id) FROM {{ ref('base_performance_reviews_current') }}) AS completed_reviews,
        (SELECT CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE ROUND(100.0 * COUNT(DISTINCT employee_id) / COUNT(*) OVER (), 2) END
            FROM {{ ref('base_talent_employee_population') }} LIMIT 1) AS completion_pct,
        (SELECT ROUND(AVG(rating), 2) FROM {{ ref('base_performance_reviews_current') }}) AS avg_rating
