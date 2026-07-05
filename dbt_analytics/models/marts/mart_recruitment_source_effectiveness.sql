{{ config(materialized='view') }}

SELECT 
        source,
        COUNT(*) AS candidate_count,
        COUNT(CASE WHEN pipeline_stage = 'Hired' THEN 1 END) AS hire_count,
        CASE 
            WHEN COUNT(*) = 0 THEN 0.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN pipeline_stage = 'Hired' THEN 1 END) / COUNT(*), 2)
        END AS conversion_pct
    FROM {{ ref('base_candidate_pipeline_current') }}
    GROUP BY source
