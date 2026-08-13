{{ config(materialized='view') }}

-- What project is this row in?
--
-- The ONLY place that question is answered. Seven marts group by project and
-- not one of them joins the locations file itself: a join repeated seven times
-- is a join nobody can change. Matrix assignment (employee x project x
-- allocation) becomes a second branch in THIS model, and the marts do not move
-- again.
--
-- `location` is the atomic unit - the site, office or yard a row belongs to.
-- `project` is a grouping ABOVE it, supplied by the client's locations file.
-- An organisation with no project concept leaves project empty, and every
-- project-level figure is then withheld rather than invented.
--
-- An empty string is normalised to NULL here so that "" and "not supplied"
-- cannot become two different buckets on a dashboard.

SELECT
    l.location,
    -- Qualified: an unqualified `project` here resolves to the output alias,
    -- not the input column, and DuckDB refuses it outright.
    NULLIF(TRIM(l.project), '') AS project,
    l.region,
    l.phase
FROM {{ ref('stg_locations') }} l
