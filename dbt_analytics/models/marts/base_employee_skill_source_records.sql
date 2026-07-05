{{ config(materialized='view') }}

SELECT
        ROW_NUMBER() OVER (ORDER BY skill_id, employee_id, skill_name) AS employee_skill_record_id,
        skill_id, employee_id, skill_name, proficiency
    FROM {{ ref('stg_employee_skills') }}
