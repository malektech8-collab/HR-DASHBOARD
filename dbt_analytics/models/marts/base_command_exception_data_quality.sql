{{ config(materialized='view') }}

SELECT 'data-quality' AS module_key, 'Data Quality' AS module_label, 'mart_data_quality_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/data-quality' AS route_path FROM {{ ref('mart_data_quality_exceptions') }}
