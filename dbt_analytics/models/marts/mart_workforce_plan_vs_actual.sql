{{ config(materialized='view') }}

SELECT 
        wp.project,
        wp.department,
        wp.planned_headcount,
        COALESCE(ahc.actual_count, 0) AS actual_headcount,
        CASE 
            WHEN wp.planned_headcount = 0 THEN 
                CASE WHEN COALESCE(ahc.actual_count, 0) = 0 THEN 100.0 ELSE 0.0 END
            ELSE ROUND(100.0 * COALESCE(ahc.actual_count, 0) / wp.planned_headcount, 2)
        END AS fulfillment_pct
    FROM {{ ref('base_workforce_plan_current') }} wp
    LEFT JOIN (
        SELECT project, department, COUNT(*) AS actual_count
        FROM {{ ref('base_active_workforce') }}
        GROUP BY 1, 2
    ) ahc ON wp.project = ahc.project AND wp.department = ahc.department
