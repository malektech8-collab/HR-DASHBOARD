{{ config(materialized='view') }}

SELECT 
        b.expiry_bucket,
        COALESCE(i.cnt, 0) AS iqama_count,
        COALESCE(w.cnt, 0) AS work_permit_count
    FROM (
        SELECT 'expired' AS expiry_bucket
        UNION ALL SELECT '0_30'
        UNION ALL SELECT '31_60'
        UNION ALL SELECT '61_90'
        UNION ALL SELECT '90_plus'
        UNION ALL SELECT 'missing_date'
    ) b
    LEFT JOIN (SELECT iqama_bucket, COUNT(*) AS cnt FROM {{ ref('base_document_expiry') }} GROUP BY iqama_bucket) i ON b.expiry_bucket = i.iqama_bucket
    LEFT JOIN (SELECT work_permit_bucket, COUNT(*) AS cnt FROM {{ ref('base_document_expiry') }} GROUP BY work_permit_bucket) w ON b.expiry_bucket = w.work_permit_bucket
