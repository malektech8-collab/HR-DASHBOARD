{{ config(materialized='view') }}

SELECT
        COALESCE(readiness, 'Missing') AS readiness,
        COUNT(DISTINCT successor_employee_id) AS successor_count
    FROM {{ ref('base_succession_plans_current') }}
    WHERE successor_employee_id IS NOT NULL AND TRIM(successor_employee_id) != ''
    GROUP BY readiness
