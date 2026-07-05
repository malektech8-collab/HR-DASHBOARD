{{ config(materialized='view') }}

SELECT 
        pipeline_stage,
        COUNT(*) AS candidate_count
    FROM {{ ref('base_candidate_pipeline_current') }}
    GROUP BY pipeline_stage
