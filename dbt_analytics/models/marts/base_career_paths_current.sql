{{ config(materialized='view') }}

SELECT * FROM {{ ref('stg_career_paths') }}
    WHERE employee_id IN (SELECT employee_id FROM {{ ref('base_talent_employee_population') }})
