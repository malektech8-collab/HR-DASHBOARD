{{ config(materialized='view') }}

SELECT c.*
    FROM {{ ref('base_candidate_canonical') }} c
    JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
    WHERE c.applied_date <= '{{ var('report_month_end') }}'
