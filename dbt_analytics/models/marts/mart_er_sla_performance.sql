{{ config(materialized='view') }}

SELECT 
        'ER' AS category_type,
        case_type AS category,
        COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) AS eligible_count,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_count,
        COUNT(CASE WHEN sla_status = 'Breached' THEN 1 END) AS breached_count,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM {{ ref('base_er_case_population') }}
    GROUP BY 1, 2
    
    UNION ALL
    
    SELECT 
        'HR_REQ' AS category_type,
        request_type AS category,
        COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) AS eligible_count,
        COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) AS compliant_count,
        COUNT(CASE WHEN sla_status = 'Breached' THEN 1 END) AS breached_count,
        CASE 
            WHEN COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END) = 0 THEN 100.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN sla_status = 'Compliant' THEN 1 END) / COUNT(CASE WHEN sla_status IN ('Compliant', 'Breached') THEN 1 END), 2)
        END AS compliance_pct
    FROM (
        SELECT r.*, s.sla_status 
        FROM {{ ref('base_hr_requests_current') }} r
        JOIN {{ ref('base_case_sla_clock') }} s ON r.request_id = s.record_id AND s.source_type = 'HR_REQ'
    )
    GROUP BY 1, 2
