{{ config(materialized='view') }}

SELECT 'compliance' AS module_key, 'Saudization & Compliance' AS module_label, 'mart_compliance_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/compliance' AS route_path FROM {{ ref('mart_compliance_exceptions') }}
