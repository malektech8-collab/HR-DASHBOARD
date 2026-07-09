{{ config(materialized='view') }}

WITH ranked AS (
        SELECT s.*,
            CASE
                WHEN s.rating >= 4.5 THEN 'Outstanding'
                WHEN s.rating >= 3.5 THEN 'Exceeds Expectations'
                WHEN s.rating >= 2.5 THEN 'Meets Expectations'
                WHEN s.rating >= 1.5 THEN 'Needs Improvement'
                WHEN s.rating IS NOT NULL THEN 'Unsatisfactory'
                ELSE NULL
            END AS performance_category,
            ROW_NUMBER() OVER (PARTITION BY s.employee_id ORDER BY s.completed_date DESC, s.performance_review_record_id DESC) AS rn
        FROM {{ ref('base_performance_review_source_records') }} s
        WHERE s.status = 'Completed'
          AND s.review_period = '{{ var('report_month') }}'
          AND s.employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
          AND s.rating IS NOT NULL
          AND s.rating BETWEEN {{ var('min_rating') }} AND {{ var('max_rating') }}
    )
    SELECT * FROM ranked WHERE rn = 1
