{{ config(materialized='view') }}

-- How much of the reporting period the client DECLARED their attendance file
-- covers. Category F made the numbers honest; this is what lets a reader see
-- why a month looks thin.
--
-- covered_days counts WORKING DAYS INSIDE THE DECLARED WINDOW, not days that
-- happen to carry rows. A day inside the window with no row is a real absence
-- (that is Category F's whole inversion), so counting rows here would
-- double-count the thing that design separated. The note answers "how much of
-- the period did you vouch for", which is the actionable fact.
--
-- DISTINCT calendar_date because the base model is one row per employee per
-- day, and this is a statement about days.
SELECT
    '{{ var('report_month') }}'                              AS report_month,
    DATE '{{ var('attendance_coverage_start') }}'            AS declared_start,
    DATE '{{ var('attendance_coverage_end') }}'              AS declared_end,
    COUNT(DISTINCT CASE WHEN coverage_status = 'covered'
                        THEN calendar_date END)              AS covered_days,
    COUNT(DISTINCT calendar_date)                            AS expected_days
FROM {{ ref('base_expected_attendance') }}
