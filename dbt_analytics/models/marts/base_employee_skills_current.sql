{{ config(materialized='view') }}

SELECT s.*
    FROM {{ ref('base_employee_skill_source_records') }} s
    WHERE s.employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
