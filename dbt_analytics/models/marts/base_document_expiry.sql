{{ config(materialized='view') }}

WITH anchor AS (
        SELECT last_day(CAST('{{ var('report_month') }}-01' AS DATE)) AS anchor_date
    )
    SELECT 
        e.employee_id,
        e.employee_name,
        e.is_saudi,
        e.iqama_expiry,
        e.work_permit_expiry,
        -- Iqama aging bucket
        --
        -- THE SEAM. `missing_date` and NULL are different findings and the
        -- distinction is the whole rule: a client who RECORDS iqama expiry and
        -- left one blank has a data-quality exception, worth flagging per
        -- employee; a client whose export has NO IQAMA COLUMN AT ALL has a
        -- coverage fact, and flagging that once per employee buries every real
        -- finding under it - the manager_id shape, measured at 2,047 of 2,047
        -- on the first real client.
        --
        -- A NULL bucket is UNMEASURABLE. Every downstream `= 'expired'` /
        -- `= '0_30'` / `= 'missing_date'` comparison is then false rather than
        -- true, so the three exception arms in mart_compliance_exceptions and
        -- the bucket join in mart_document_expiry withhold without an edit.
        -- The COUNTs cannot be left to it - COUNT of a never-true CASE is 0,
        -- not NULL - so those are gated at their own site.
        CASE
            WHEN NOT {{ var('has_iqama_expiry_source_sql') }} THEN NULL
            WHEN e.iqama_expiry IS NULL THEN 'missing_date'
            WHEN e.iqama_expiry < a.anchor_date THEN 'expired'
            WHEN e.iqama_expiry >= a.anchor_date AND e.iqama_expiry <= a.anchor_date + 30 THEN '0_30'
            WHEN e.iqama_expiry > a.anchor_date + 30 AND e.iqama_expiry <= a.anchor_date + 60 THEN '31_60'
            WHEN e.iqama_expiry > a.anchor_date + 60 AND e.iqama_expiry <= a.anchor_date + 90 THEN '61_90'
            ELSE '90_plus'
        END AS iqama_bucket,
        -- Work Permit aging bucket
        CASE 
            WHEN e.work_permit_expiry IS NULL THEN 'missing_date'
            WHEN e.work_permit_expiry < a.anchor_date THEN 'expired'
            WHEN e.work_permit_expiry >= a.anchor_date AND e.work_permit_expiry <= a.anchor_date + 30 THEN '0_30'
            WHEN e.work_permit_expiry > a.anchor_date + 30 AND e.work_permit_expiry <= a.anchor_date + 60 THEN '31_60'
            WHEN e.work_permit_expiry > a.anchor_date + 60 AND e.work_permit_expiry <= a.anchor_date + 90 THEN '61_90'
            ELSE '90_plus'
        END AS work_permit_bucket
    FROM {{ ref('base_compliance_current') }} e
    CROSS JOIN anchor a
    WHERE e.is_saudi = FALSE AND e.nationality IS NOT NULL AND TRIM(e.nationality) != ''
