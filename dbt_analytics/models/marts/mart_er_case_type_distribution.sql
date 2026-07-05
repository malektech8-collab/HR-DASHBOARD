{{ config(materialized='view') }}

SELECT 
        case_type,
        COUNT(*) AS case_count
    FROM {{ ref('base_er_case_population') }}
    GROUP BY case_type
