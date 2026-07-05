{{ config(materialized='view') }}

SELECT 
        employee_id,
        employee_name,
        issue_type,
        description,
        severity,
        recommended_action
    FROM {{ ref('stg_data_quality') }}
