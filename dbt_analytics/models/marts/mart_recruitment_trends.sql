{{ config(materialized='view') }}

-- Simulated historical trend for MVP visuals
    SELECT '2026-04' AS period, 5 AS requisitions_opened, 3 AS hires
    UNION ALL
    SELECT '2026-05' AS period, 6 AS requisitions_opened, 4 AS hires
    UNION ALL
    -- Live dynamic current period
    SELECT 
        '{rec_report_month}' AS period,
        COUNT(CASE WHEN approval_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS requisitions_opened,
        COUNT(CASE WHEN hire_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS hires
    FROM (
        SELECT r.approval_date, o.hire_date
        FROM {{ ref('base_recruitment_requisitions_current') }} r
        LEFT JOIN {{ ref('base_candidate_canonical') }} c ON r.requisition_id = c.requisition_id
        LEFT JOIN {{ ref('base_onboarding_source_records') }} o ON c.candidate_id = o.candidate_id
    )
