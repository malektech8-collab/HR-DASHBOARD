{{ config(materialized='view') }}

SELECT module_key, page_key, route_path, 'Registered' AS status FROM {{ ref('base_command_center_module_registry') }}
