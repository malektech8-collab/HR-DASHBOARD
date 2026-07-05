{{ config(materialized='view') }}

SELECT 
        r.department,
        r.project,
        COALESCE(ROUND(AVG(ob.hire_date - r.approval_date), 1), 0.0) AS average_time_to_fill,
        COUNT(ob.onboarding_record_id) AS hire_count
    FROM {{ ref('base_onboarding_source_records') }} ob
    JOIN {{ ref('base_candidate_canonical') }} c ON ob.candidate_id = c.candidate_id
    JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
    WHERE ob.hire_date IS NOT NULL AND r.approval_date IS NOT NULL
    GROUP BY r.department, r.project
