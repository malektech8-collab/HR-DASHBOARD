{{ config(materialized='view') }}

WITH anchor AS (
        SELECT last_day(CAST('{{ var('report_month') }}-01' AS DATE)) AS anchor_date
    )
    -- EVERY bucket is gated, including `missing_date`, and gating all six
    -- together is the point. Five of them read 0 and the sixth read the whole
    -- non-Saudi roster when the client's export has no iqama column, so the
    -- chart said "nothing expired, nothing expiring, and every one of your
    -- employees is missing a date" - three claims, all false, from one absent
    -- column. Withheld as a whole, the card renders as unmeasurable.
    --
    -- This mart is where the two defects met: SP-011 had it suppressed on a
    -- compliance file it never reads, so the zeros never reached a screen
    -- until that suppression was correctly removed. See SP-013.
    SELECT
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry < (SELECT anchor_date FROM anchor) THEN e.employee_id END) END AS expired,
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) AND (SELECT anchor_date FROM anchor) + INTERVAL 30 DAY THEN e.employee_id END) END AS "0_30",
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 31 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 60 DAY THEN e.employee_id END) END AS "31_60",
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry BETWEEN (SELECT anchor_date FROM anchor) + INTERVAL 61 DAY AND (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN e.employee_id END) END AS "61_90",
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry > (SELECT anchor_date FROM anchor) + INTERVAL 90 DAY THEN e.employee_id END) END AS "90_plus",
        CASE WHEN {{ var('has_iqama_expiry_source_sql') }} THEN COUNT(DISTINCT CASE WHEN e.iqama_expiry IS NULL THEN e.employee_id END) END AS missing_date
    FROM {{ ref('base_active_workforce') }} e
    WHERE e.is_saudi = FALSE
