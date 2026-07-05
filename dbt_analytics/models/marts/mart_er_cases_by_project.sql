{{ config(materialized='view') }}

SELECT 
        project,
        COUNT(*) AS total_cases,
        COUNT(CASE WHEN case_status IN ('Open', 'In Progress', 'Pending') THEN 1 END) AS open_cases,
        COUNT(CASE WHEN case_status = 'Closed' THEN 1 END) AS closed_cases,
        COUNT(CASE WHEN escalated = TRUE THEN 1 END) AS escalated_cases,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_cases,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM {{ ref('base_er_case_population') }}
    GROUP BY project
