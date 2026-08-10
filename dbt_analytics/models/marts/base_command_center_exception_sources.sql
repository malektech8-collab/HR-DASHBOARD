{{ config(materialized='view') }}

WITH raw_exceptions AS (
        SELECT * FROM {{ ref('base_command_exception_data_quality') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_workforce') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_payroll') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_attendance') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_compliance') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_er') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_recruitment') }} UNION ALL
        SELECT * FROM {{ ref('base_command_exception_talent') }}
    )
    SELECT 
        module_key,
        module_label,
        source_mart,
        entity_id,
        entity_name,
        issue_type,
        description,
        CASE LOWER(TRIM(severity))
            WHEN 'critical' THEN 'Critical'
            WHEN 'warning' THEN 'Warning'
            WHEN 'info' THEN 'Info'
            ELSE 'Unknown'
        END AS severity,
        recommended_action,
        route_path
    FROM raw_exceptions
