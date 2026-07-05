{{ config(materialized='view') }}

SELECT 
        module_key,
        module_label,
        severity,
        issue_type,
        COUNT(*) AS exception_count,
        MAX(recommended_action) AS recommended_action,
        MAX(route_path) AS route_path
    FROM {{ ref('base_command_center_exception_sources') }}
    GROUP BY module_key, module_label, severity, issue_type
