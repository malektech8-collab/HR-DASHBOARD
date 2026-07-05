{{ config(materialized='view') }}

SELECT 
        employee_id,
        employee_name,
        nationality,
        is_saudi,
        project,
        department,
        CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 ELSE 0 END AS saudi_count,
        CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 ELSE 0 END AS non_saudi_count,
        CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 ELSE 0 END AS missing_nationality_count
    FROM {{ ref('base_active_workforce') }}
