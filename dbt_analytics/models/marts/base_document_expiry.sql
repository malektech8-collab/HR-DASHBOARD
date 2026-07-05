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
        CASE 
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
