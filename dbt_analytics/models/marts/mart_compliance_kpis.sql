{{ config(materialized='view') }}

WITH counts AS (
        SELECT 
            COUNT(CASE WHEN is_saudi = TRUE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS saudi_hc,
            COUNT(CASE WHEN is_saudi = FALSE AND nationality IS NOT NULL AND TRIM(nationality) != '' THEN 1 END) AS non_saudi_hc,
            COUNT(CASE WHEN nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL THEN 1 END) AS missing_nationality
        FROM {{ ref('base_active_workforce') }}
    ),
    expiries AS (
        SELECT 
            -- Withheld, not zero. 0 reads as "nobody's iqama has expired",
            -- which is a claim an absent column does not make - and the one
            -- claim in this product a client must never be given falsely.
            CASE WHEN {{ var('has_iqama_expiry_source_sql') }}
                 THEN COUNT(CASE WHEN iqama_bucket = '0_30' THEN 1 END)
            END AS iqamas_expiring_30,
            CASE WHEN {{ var('has_iqama_expiry_source_sql') }}
                 THEN COUNT(CASE WHEN iqama_bucket = 'expired' THEN 1 END)
            END AS iqamas_expired,
            COUNT(CASE WHEN work_permit_bucket = '0_30' THEN 1 END) AS work_permits_expiring_30,
            COUNT(CASE WHEN work_permit_bucket = 'expired' THEN 1 END) AS work_permits_expired
        FROM {{ ref('base_document_expiry') }}
    ),
    gosi_wps AS (
        SELECT 
            COUNT(CASE WHEN gosi_status != 'Registered' OR gosi_status IS NULL THEN 1 END) AS gosi_not_registered,
            COUNT(CASE WHEN mudad_status != 'Compliant' OR mudad_status IS NULL THEN 1 END) AS wps_exceptions
        FROM {{ ref('base_compliance_current') }}
    ),
    exc_count AS (
        SELECT COUNT(*) AS exception_count FROM {{ ref('mart_compliance_exceptions') }}
    )
    SELECT 
        c.saudi_hc AS saudi_headcount,
        c.non_saudi_hc AS non_saudi_headcount,
        c.missing_nationality AS employees_missing_nationality,
        CASE 
            WHEN (c.saudi_hc + c.non_saudi_hc) = 0 THEN 0.0
            ELSE ROUND(100.0 * c.saudi_hc / (c.saudi_hc + c.non_saudi_hc), 2)
        END AS saudization_pct,
        e.iqamas_expiring_30,
        e.work_permits_expiring_30,
        e.iqamas_expired,
        e.work_permits_expired,
        gw.gosi_not_registered AS gosi_missing_count,
        gw.wps_exceptions AS wps_exception_count,
        ex.exception_count AS compliance_exception_count
    FROM counts c
    CROSS JOIN expiries e
    CROSS JOIN gosi_wps gw
    CROSS JOIN exc_count ex
