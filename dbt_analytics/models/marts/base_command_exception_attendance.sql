{{ config(materialized='view') }}

SELECT 'attendance' AS module_key, 'Attendance' AS module_label, 'mart_attendance_exceptions' AS source_mart, employee_id AS entity_id, employee_name AS entity_name, issue_type, description, severity, recommended_action, '/attendance' AS route_path FROM {{ ref('mart_attendance_exceptions') }}
