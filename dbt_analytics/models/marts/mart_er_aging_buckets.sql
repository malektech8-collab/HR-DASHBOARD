{{ config(materialized='view') }}

SELECT 
        CASE 
            WHEN aging_days BETWEEN 0 AND 3 THEN '0_3_days'
            WHEN aging_days BETWEEN 4 AND 7 THEN '4_7_days'
            WHEN aging_days BETWEEN 8 AND 14 THEN '8_14_days'
            WHEN aging_days BETWEEN 15 AND 30 THEN '15_30_days'
            ELSE '30_plus_days'
        END AS aging_bucket,
        COUNT(*) AS case_count
    FROM {{ ref('base_er_case_population') }}
    WHERE case_status IN ('Open', 'In Progress', 'Pending')
    GROUP BY 1
