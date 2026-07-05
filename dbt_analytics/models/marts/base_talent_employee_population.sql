{{ config(materialized='view') }}

SELECT employee_id, employee_name, department, project, job_title, status
    FROM {{ ref('base_active_workforce') }}
    WHERE employee_id IS NOT NULL AND TRIM(employee_id) != ''
