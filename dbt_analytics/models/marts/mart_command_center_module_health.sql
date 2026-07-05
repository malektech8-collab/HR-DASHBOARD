{{ config(materialized='view') }}

SELECT 
        module_key,
        module_label,
        route_path,
        owner_domain,
        api_health_status,
        reconciliation_status,
        required_marts_present,
        stale_flag,
        critical_exception_count,
        warning_exception_count,
        CASE 
            WHEN api_health_status = 'Unhealthy' OR required_marts_present = FALSE OR reconciliation_status = 'Failed' OR critical_exception_count > 0 THEN 'Critical'
            WHEN api_health_status = 'Unknown' OR reconciliation_status = 'Unknown' THEN 'Unknown'
            WHEN warning_exception_count > 0 OR stale_flag = TRUE THEN 'Warning'
            WHEN api_health_status = 'Healthy' AND required_marts_present = TRUE AND reconciliation_status = 'Passed' AND stale_flag = FALSE AND critical_exception_count = 0 AND warning_exception_count = 0 THEN 'Healthy'
            ELSE 'Unknown'
        END AS status,
        primary_kpi_count,
        screenshot_path,
        qa_report_path
    FROM {{ ref('base_command_center_module_status') }}
