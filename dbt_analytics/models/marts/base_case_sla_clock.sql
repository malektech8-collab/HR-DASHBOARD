{{ config(materialized='view') }}

WITH er_sla_prep AS (
        SELECT 
            c.er_case_record_id,
            c.created_date,
            c.closed_date,
            c.case_type,
            c.case_status,
            c.target_due_date,
            CASE 
                WHEN c.case_type = 'Disciplinary' THEN {{ var('disciplinary_sla_days') }}
                WHEN c.case_type = 'Grievance' THEN {{ var('grievance_sla_days') }}
                WHEN c.case_type = 'Labor Case' THEN {{ var('labor_case_sla_days') }}
                ELSE 14
            END AS config_sla_days
        FROM {{ ref('base_er_cases_current') }} c
    ),
    er_sla_effective AS (
        SELECT 
            er_case_record_id,
            case_status,
            created_date,
            closed_date,
            COALESCE(target_due_date, created_date + config_sla_days) AS effective_target_due_date
        FROM er_sla_prep
    )
    SELECT 
        'ER' AS source_type,
        er_case_record_id AS record_id,
        effective_target_due_date AS effective_due_date,
        CASE 
            WHEN closed_date IS NOT NULL THEN (closed_date - created_date)
            ELSE ('{{ var('report_anchor_date') }}' - created_date)
        END AS aging_days,
        CASE 
            WHEN created_date IS NULL OR effective_target_due_date IS NULL THEN 'Not Eligible'
            WHEN closed_date IS NOT NULL AND closed_date <= effective_target_due_date THEN 'Compliant'
            WHEN closed_date IS NOT NULL AND closed_date > effective_target_due_date THEN 'Breached'
            WHEN closed_date IS NULL AND '{{ var('report_anchor_date') }}' > effective_target_due_date THEN 'Breached'
            ELSE 'Pending'
        END AS sla_status
    FROM er_sla_effective

    UNION ALL

    SELECT 
        'HR_REQ' AS source_type,
        request_id AS record_id,
        NULL AS effective_due_date,
        CASE 
            WHEN closed_at IS NOT NULL THEN (CAST(closed_at AS DATE) - CAST(created_at AS DATE))
            ELSE ('{{ var('report_anchor_date') }}' - CAST(created_at AS DATE))
        END AS aging_days,
        CASE 
            WHEN sla_hours IS NULL THEN 'Not Eligible'
            WHEN actual_hours <= sla_hours THEN 'Compliant'
            ELSE 'Breached'
        END AS sla_status
    FROM {{ ref('base_hr_requests_current') }}
