{{ config(materialized='view') }}

SELECT 
        (SELECT report_month FROM {{ ref('base_command_center_report_context') }}) AS report_month,
        ARRAY(SELECT DISTINCT company FROM {{ ref('stg_employees') }} WHERE company IS NOT NULL) AS companies,
        ARRAY(SELECT DISTINCT project FROM {{ ref('stg_employees') }} WHERE project IS NOT NULL) AS projects,
        ARRAY(SELECT DISTINCT department FROM {{ ref('stg_employees') }} WHERE department IS NOT NULL) AS departments,
        ARRAY(SELECT DISTINCT cost_center FROM {{ ref('stg_employees') }} WHERE cost_center IS NOT NULL) AS cost_centers,
        CAST([] AS VARCHAR[]) AS locations,
        ARRAY(SELECT DISTINCT nationality FROM {{ ref('stg_employees') }} WHERE nationality IS NOT NULL) AS nationalities,
        ARRAY(SELECT DISTINCT module_key FROM {{ ref('base_command_center_module_registry') }}) AS modules
