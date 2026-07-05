{{ config(materialized='view') }}

WITH er_counts AS (
        SELECT 
            COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') THEN 1 END) AS open_cases,
            COUNT(CASE WHEN created_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS new_cases,
            COUNT(CASE WHEN closed_date BETWEEN '{{ var('report_month_start') }}' AND '{{ var('report_month_end') }}' THEN 1 END) AS closed_cases,
            ROUND(AVG(aging_days), 1) AS avg_aging,
            COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') AND '{{ var('report_anchor_date') }}' > effective_target_due_date THEN 1 END) AS overdue_cases,
            COUNT(CASE WHEN case_type = 'Disciplinary' THEN 1 END) AS disciplinary_cases,
            COUNT(CASE WHEN case_type = 'Grievance' THEN 1 END) AS grievance_cases,
            COUNT(CASE WHEN case_type = 'Labor Case' THEN 1 END) AS labor_cases,
            COUNT(CASE WHEN escalated = TRUE THEN 1 END) AS escalated_cases
        FROM {{ ref('base_er_case_population') }}
    ),
    er_sla AS (
        SELECT 
            ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / 
                  NULLIF(COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 0), 2) AS er_sla_compliance
        FROM {{ ref('base_er_case_population') }}
    ),
    exc AS (
        SELECT COUNT(*) AS exception_count FROM {{ ref('mart_er_exceptions') }}
    )
    SELECT 
        c.open_cases AS total_open_er_cases,
        c.new_cases AS new_cases_this_month,
        c.closed_cases AS closed_cases_this_month,
        COALESCE(c.avg_aging, 0.0) AS average_case_aging_days,
        c.overdue_cases AS overdue_cases,
        COALESCE(s.er_sla_compliance, 100.0) AS sla_compliance_pct,
        c.disciplinary_cases AS disciplinary_cases,
        c.grievance_cases AS grievance_cases,
        c.labor_cases AS labor_cases,
        c.escalated_cases AS escalated_cases,
        ex.exception_count AS er_exception_count
    FROM er_counts c
    CROSS JOIN er_sla s
    CROSS JOIN exc ex
