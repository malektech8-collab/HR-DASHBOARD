{{ config(materialized='view') }}

SELECT 
        module_key || '_' || issue_type AS alert_id,
        module_key,
        module_label,
        severity,
        issue_type,
        COUNT(*) AS issue_count,
        MAX(recommended_action) AS recommended_action,
        MAX(source_mart) AS source_mart,
        MAX(route_path) AS route_path
    FROM {{ ref('base_command_center_exception_sources') }}
    GROUP BY module_key, module_label, severity, issue_type
    ORDER BY CASE WHEN severity = 'Critical' THEN 1 ELSE 2 END ASC, issue_count DESC
