{{ config(materialized='view') }}

WITH errs AS (
        SELECT 
            module_key,
            COUNT(CASE WHEN severity = 'Critical' THEN 1 END) AS critical_exception_count,
            COUNT(CASE WHEN severity = 'Warning' THEN 1 END) AS warning_exception_count
        FROM {{ ref('base_command_center_exception_sources') }}
        GROUP BY module_key
    ),
    fresh AS (
        SELECT 
            module_key, 
            stale_flag
        FROM {{ ref('mart_command_center_data_freshness') }}
    )
    SELECT 
        reg.module_key,
        reg.module_label,
        reg.route_path,
        reg.owner_domain,
        COALESCE(chk.api_health_status, 'Unknown') AS api_health_status,
        COALESCE(chk.reconciliation_status, 'Unknown') AS reconciliation_status,
        COALESCE(chk.required_marts_present, FALSE) AS required_marts_present,
        COALESCE(f.stale_flag, FALSE) AS stale_flag,
        COALESCE(e.critical_exception_count, 0) AS critical_exception_count,
        COALESCE(e.warning_exception_count, 0) AS warning_exception_count,
        reg.primary_kpi_count,
        reg.screenshot_path,
        reg.qa_report_path
    FROM {{ ref('base_command_center_module_registry') }} reg
    LEFT JOIN errs e ON reg.module_key = e.module_key
    LEFT JOIN fresh f ON reg.module_key = f.module_key
    LEFT JOIN command_center_module_checks chk ON reg.module_key = chk.module_key
