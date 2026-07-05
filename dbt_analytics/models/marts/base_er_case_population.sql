{{ config(materialized='view') }}

SELECT 
        c.*, 
        s.aging_days, 
        s.sla_status,
        s.effective_due_date AS effective_target_due_date
    FROM {{ ref('base_er_cases_current') }} c
    JOIN {{ ref('base_case_sla_clock') }} s ON c.er_case_record_id = s.record_id AND s.source_type = 'ER'
