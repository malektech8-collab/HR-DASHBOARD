{{ config(materialized='view') }}

SELECT 
        status AS onboarding_status,
        COUNT(*) AS hire_count
    FROM {{ ref('base_onboarding_current') }}
    GROUP BY status
