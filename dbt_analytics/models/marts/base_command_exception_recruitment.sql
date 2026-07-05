{{ config(materialized='view') }}

SELECT 'recruitment' AS module_key, 'Recruitment & Hiring' AS module_label, 'mart_recruitment_exceptions' AS source_mart, record_id_str AS entity_id, CAST(NULL AS VARCHAR) AS entity_name, issue_type, description, severity, recommended_action, '/recruitment' AS route_path FROM {{ ref('mart_recruitment_exceptions') }}
