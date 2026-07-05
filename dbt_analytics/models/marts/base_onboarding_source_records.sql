{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY onboarding_id, candidate_id, start_date) AS onboarding_record_id,
        onboarding_id,
        candidate_id,
        start_date AS hire_date,
        status,
        employee_id
    FROM {{ ref('stg_onboarding') }}
