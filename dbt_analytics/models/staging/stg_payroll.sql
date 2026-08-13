-- `location` is what the client supplies; `project` is RESOLVED from their
-- locations file through base_row_project, never read off the row. Resolving
-- here means the 33 downstream models that name `project` keep working
-- unchanged and are correct by construction - the alternative was editing all
-- of them and hoping none was missed.
--
-- LEFT JOIN, deliberately: a row whose site is absent from the locations file
-- keeps its row and its measures, and gets project = NULL. It is counted in
-- every total and excluded from the project breakdown, and mart_unmatched_
-- locations tells the client which sites are missing. Dropping the row would
-- silently change a headcount; bucketing it as 'Unassigned' would render an
-- absence as a grouping.

SELECT
    f.*,
    p.project
FROM {{ source('hr_raw', 'payroll') }} f
LEFT JOIN {{ ref('base_row_project') }} p ON f.location = p.location
