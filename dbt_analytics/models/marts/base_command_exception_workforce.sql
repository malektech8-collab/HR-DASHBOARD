{{ config(materialized='view') }}

SELECT 'workforce' AS module_key, 'Workforce' AS module_label, 'mart_workforce_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/workforce' AS route_path FROM {{ ref('mart_workforce_exceptions') }}
