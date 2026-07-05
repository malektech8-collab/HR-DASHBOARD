{{ config(materialized='view') }}

SELECT ob.*
    FROM {{ ref('base_onboarding_source_records') }} ob
    JOIN {{ ref('base_candidate_canonical') }} c ON ob.candidate_id = c.candidate_id
    JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
    WHERE ob.hire_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}'
