{{ config(materialized='view') }}

SELECT performance_category, COUNT(DISTINCT employee_id) AS employee_count
    FROM {{ ref('base_performance_reviews_current') }}
    GROUP BY performance_category
