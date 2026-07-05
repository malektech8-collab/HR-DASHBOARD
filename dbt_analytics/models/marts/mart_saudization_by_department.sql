{{ config(materialized='view') }}

SELECT 
        COALESCE(department, 'Unassigned') AS department,
        COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS saudi_headcount,
        COUNT(CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS non_saudi_headcount,
        COUNT(CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 END) AS employees_missing_nationality,
        COUNT(*) AS total_headcount,
        CASE 
            WHEN COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END) = 0 THEN 0.0
            ELSE ROUND(100.0 * COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) / COUNT(CASE WHEN is_saudi = TRUE OR (is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '') THEN 1 END), 2)
        END AS saudization_pct
    FROM {{ ref('base_active_workforce') }}
    GROUP BY department
