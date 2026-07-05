{{ config(materialized='view') }}

WITH req_stats AS (
        SELECT 
            COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') THEN 1 END) AS open_reqs,
            COUNT(CASE WHEN status IN ('Open', 'Approved', 'In Progress', 'On Hold') AND '{{ var('report_anchor_date') }}' > effective_target_hire_date THEN 1 END) AS overdue_reqs
        FROM {{ ref('base_recruitment_requisitions_current') }}
    ),
    vac_stats AS (
        SELECT COALESCE(SUM(quantity), 0) AS approved_vacancies
        FROM {{ ref('base_vacancy_population') }}
    ),
    cand_stats AS (
        SELECT COUNT(*) AS cand_in_pipeline
        FROM {{ ref('base_candidate_pipeline_current') }}
    ),
    int_stats AS (
        SELECT COUNT(*) AS interviews_scheduled
        FROM {{ ref('base_interview_activity_current') }}
    ),
    off_stats AS (
        SELECT 
            COUNT(*) AS offers_extended,
            COUNT(CASE WHEN offer_status = 'Accepted' THEN 1 END) AS accepted_offers,
            COUNT(CASE WHEN offer_status IN ('Accepted', 'Rejected', 'Declined') THEN 1 END) AS decided_offers
        FROM {{ ref('base_offer_activity_current') }}
    ),
    hire_stats AS (
        SELECT COUNT(*) AS hires_this_month
        FROM {{ ref('base_onboarding_current') }}
    ),
    ttf_stats AS (
        SELECT 
            COALESCE(ROUND(AVG(ob.hire_date - r.approval_date), 1), 0.0) AS avg_time_to_fill
        FROM {{ ref('base_onboarding_source_records') }} ob
        JOIN {{ ref('base_candidate_canonical') }} c ON ob.candidate_id = c.candidate_id
        JOIN {{ ref('base_recruitment_requisitions_current') }} r ON c.requisition_id = r.requisition_id
        WHERE ob.hire_date IS NOT NULL AND r.approval_date IS NOT NULL
    ),
    plan_fulfillment AS (
        SELECT 
            CASE 
                WHEN planned.total_planned = 0 THEN 
                    CASE WHEN actual.total_actual = 0 THEN 100.0 ELSE 0.0 END
                ELSE ROUND(100.0 * actual.total_actual / planned.total_planned, 2)
            END AS plan_fulfillment_pct
        FROM (
            SELECT COALESCE(SUM(planned_headcount), 0) AS total_planned 
            FROM {{ ref('base_workforce_plan_current') }}
        ) planned
        CROSS JOIN (
            SELECT COUNT(aw.employee_id) AS total_actual
            FROM {{ ref('base_workforce_plan_current') }} wp
            LEFT JOIN {{ ref('base_active_workforce') }} aw ON wp.project = aw.project AND wp.department = aw.department
        ) actual
    ),
    exc_stats AS (
        SELECT COUNT(*) AS exception_count FROM {{ ref('mart_recruitment_exceptions') }}
    )
    SELECT 
        r.open_reqs AS open_requisitions,
        v.approved_vacancies AS approved_vacancies,
        c.cand_in_pipeline AS candidates_in_pipeline,
        i.interviews_scheduled AS interviews_scheduled,
        o.offers_extended AS offers_extended,
        CASE 
            WHEN o.decided_offers = 0 THEN 100.0
            ELSE ROUND(100.0 * o.accepted_offers / o.decided_offers, 2)
        END AS offer_acceptance_pct,
        h.hires_this_month AS hires_this_month,
        t.avg_time_to_fill AS average_time_to_fill,
        r.overdue_reqs AS overdue_requisitions,
        COALESCE(p.plan_fulfillment_pct, 100.0) AS workforce_plan_fulfillment_pct,
        ex.exception_count AS recruitment_exception_count
    FROM req_stats r
    CROSS JOIN vac_stats v
    CROSS JOIN cand_stats c
    CROSS JOIN int_stats i
    CROSS JOIN off_stats o
    CROSS JOIN hire_stats h
    CROSS JOIN ttf_stats t
    CROSS JOIN plan_fulfillment p
    CROSS JOIN exc_stats ex
