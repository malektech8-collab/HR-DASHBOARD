{{ config(materialized='view') }}

SELECT 'department' AS category, COALESCE(department, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('base_active_workforce') }}
    GROUP BY department
    UNION ALL
    SELECT 'project' AS category, COALESCE(project, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('base_active_workforce') }}
    GROUP BY project
    UNION ALL
    SELECT 'nationality_group' AS category, CASE WHEN is_saudi = TRUE THEN 'Saudi' ELSE 'Non-Saudi' END AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('base_active_workforce') }}
    GROUP BY is_saudi
    UNION ALL
    SELECT 'employment_type' AS category, COALESCE(employment_type, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('base_active_workforce') }}
    GROUP BY employment_type
    UNION ALL
    SELECT 'status' AS category, COALESCE(status, 'Missing') AS metric_value, COUNT(DISTINCT employee_id) AS headcount
    FROM {{ ref('base_active_workforce') }}
    GROUP BY status
