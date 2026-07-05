{{ config(materialized='view') }}

SELECT o.*
    FROM {{ ref('base_offer_source_records') }} o
    JOIN {{ ref('base_candidate_canonical') }} c ON o.candidate_id = c.candidate_id
    JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
    WHERE o.offer_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}'
