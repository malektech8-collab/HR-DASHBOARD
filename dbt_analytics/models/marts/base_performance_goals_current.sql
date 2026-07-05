{{ config(materialized='view') }}

SELECT g.*
    FROM {{ ref('base_performance_goal_source_records') }} g
    WHERE g.employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
      AND g.status IS NOT NULL
