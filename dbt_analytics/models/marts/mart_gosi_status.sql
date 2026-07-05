{{ config(materialized='view') }}

SELECT 
        CASE 
            WHEN gosi_status = 'Registered' THEN 'Registered'
            WHEN gosi_status IS NOT NULL THEN 'Not Registered'
            ELSE 'Missing Source / Unknown'
        END AS gosi_status,
        COUNT(*) AS employee_count
    FROM {{ ref('base_compliance_current') }}
    GROUP BY 1
