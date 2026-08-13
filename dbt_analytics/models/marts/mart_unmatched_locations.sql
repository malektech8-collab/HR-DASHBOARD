{{ config(materialized='view') }}

-- Sites that appear on a client's data but not in their locations file.
--
-- This is an EXCEPTION, not a bucket. The previous shape was
-- `COALESCE(project, 'Unassigned')` in one mart and
-- `COALESCE(project, 'Missing Project')` in another - two sentinels for one
-- condition, each rendering an absence as a slice of a pie chart that looks
-- like a real grouping.
--
-- The row still counts in every total. What the client gets is a named list of
-- the sites they need to add, which is the actionable form of the same fact.

WITH used AS (
    SELECT DISTINCT location, 'employees' AS source_table
    FROM {{ ref('stg_employees') }} WHERE location IS NOT NULL
    UNION
    SELECT DISTINCT location, 'payroll' FROM {{ ref('stg_payroll') }}
    WHERE location IS NOT NULL
    UNION
    SELECT DISTINCT location, 'attendance' FROM {{ ref('stg_attendance') }}
    WHERE location IS NOT NULL
    UNION
    SELECT DISTINCT location, 'hr_requests' FROM {{ ref('stg_hr_requests') }}
    WHERE location IS NOT NULL
)
SELECT
    u.location,
    u.source_table,
    'Missing Location' AS issue_type,
    'This site is used in your data but is not listed in your locations file, '
        || 'so its rows cannot be grouped into a project.' AS description,
    'Warning' AS severity,
    'Add this site to your locations file and re-upload it.'
        AS recommended_action
FROM used u
LEFT JOIN {{ ref('base_row_project') }} p ON u.location = p.location
WHERE p.location IS NULL
