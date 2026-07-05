{{ config(materialized='view') }}

SELECT 
        case_status,
        COUNT(*) AS case_count
    FROM {{ ref('base_er_case_population') }}
    GROUP BY case_status
