{{ config(materialized='view') }}

SELECT 'er' AS module_key, 'Employee Relations' AS module_label, 'mart_er_exceptions' AS source_mart, case_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/er' AS route_path FROM {{ ref('mart_er_exceptions') }}
