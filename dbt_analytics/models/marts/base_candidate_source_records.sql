{{ config(materialized='view') }}

SELECT 
        row_number() OVER (ORDER BY candidate_id, candidate_name, requisition_id, applied_date) AS candidate_record_id,
        candidate_id,
        candidate_name,
        CASE 
            WHEN source IN ('LinkedIn', 'Indeed', 'Referral', 'Direct', 'Agency') THEN source
            ELSE 'Other'
        END AS source,
        source AS raw_source,
        pipeline_stage,
        requisition_id,
        applied_date
    FROM {{ ref('stg_candidates') }}
