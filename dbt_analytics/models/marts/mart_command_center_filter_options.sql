{{ config(materialized='view') }}

SELECT 
        (SELECT report_month FROM {{ ref('base_command_center_report_context') }}) AS report_month,
        ARRAY(SELECT DISTINCT company FROM {{ ref('stg_employees') }} WHERE company IS NOT NULL) AS companies,
        -- Projects come from the REFERENCE FILE, not from employee rows: the
        -- client's locations file is what says which projects exist. A client
        -- with no locations file gets an empty list because they have not told
        -- us their projects, which is a different thing from having none.
        ARRAY(SELECT DISTINCT project FROM {{ ref('base_row_project') }} WHERE project IS NOT NULL) AS projects,
        ARRAY(SELECT DISTINCT department FROM {{ ref('stg_employees') }} WHERE department IS NOT NULL) AS departments,
        ARRAY(SELECT DISTINCT cost_center FROM {{ ref('stg_employees') }} WHERE cost_center IS NOT NULL) AS cost_centers,
        -- Was hardcoded to []. An empty array claims "this client has no
        -- locations", which was never true - nothing had ever populated it.
        ARRAY(SELECT DISTINCT location FROM {{ ref('stg_employees') }} WHERE location IS NOT NULL) AS locations,
        ARRAY(SELECT DISTINCT nationality FROM {{ ref('stg_employees') }} WHERE nationality IS NOT NULL) AS nationalities,
        ARRAY(SELECT DISTINCT module_key FROM {{ ref('base_command_center_module_registry') }}) AS modules
