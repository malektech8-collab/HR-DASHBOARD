{{ config(materialized='view') }}

SELECT i.*
    FROM {{ ref('base_interview_source_records') }} i
    JOIN {{ ref('base_candidate_canonical') }} c ON i.candidate_id = c.candidate_id
    JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
    WHERE i.interview_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }} 23:59:59'
