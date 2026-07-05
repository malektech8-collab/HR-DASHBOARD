{{ config(materialized='view') }}

SELECT
        competency_name,
        ROUND(AVG(required_score), 2) AS avg_required,
        ROUND(AVG(actual_score), 2) AS avg_actual,
        ROUND(AVG(required_score - actual_score), 2) AS avg_gap
    FROM {{ ref('base_competency_assessments_current') }}
    GROUP BY competency_name
    ORDER BY avg_gap DESC
