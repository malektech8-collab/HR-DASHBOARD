{{ config(materialized='view') }}

SELECT c.*
    FROM {{ ref('base_competency_source_records') }} c
    WHERE c.employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
      AND c.required_score BETWEEN {{ var('min_rating') }} AND {{ var('max_rating') }}
      AND c.actual_score BETWEEN {{ var('min_rating') }} AND {{ var('max_rating') }}
