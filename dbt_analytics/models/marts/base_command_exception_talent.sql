{{ config(materialized='view') }}

SELECT 'talent' AS module_key, 'Talent & Succession' AS module_label, 'mart_talent_exceptions' AS source_mart, record_id_str AS entity_id, CAST(NULL AS VARCHAR) AS entity_name, issue_type, description, severity, recommended_action, '/talent' AS route_path FROM {{ ref('mart_talent_exceptions') }}
