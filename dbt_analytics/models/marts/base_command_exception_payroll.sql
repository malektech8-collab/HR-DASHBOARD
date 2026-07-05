{{ config(materialized='view') }}

SELECT 'payroll' AS module_key, 'Payroll & Cost' AS module_label, 'mart_payroll_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/payroll' AS route_path FROM {{ ref('mart_payroll_exceptions') }}
