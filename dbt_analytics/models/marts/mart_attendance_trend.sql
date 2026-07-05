{{ config(materialized='view') }}

SELECT 
        '2026-04' AS month,
        0.965 AS attendance_compliance_pct,
        2.0 AS absence_days,
        180.0 AS late_minutes,
        120.0 AS net_late_minutes,
        1.0 AS missing_punch_count,
        8.0 AS overtime_hours
    UNION ALL
    SELECT 
        '2026-05' AS month,
        0.950 AS attendance_compliance_pct,
        3.0 AS absence_days,
        240.0 AS late_minutes,
        180.0 AS net_late_minutes,
        2.0 AS missing_punch_count,
        12.5 AS overtime_hours
    UNION ALL
    SELECT 
        '2026-06' AS month,
        ROUND(attendance_compliance_pct, 4) AS attendance_compliance_pct,
        absence_days,
        CAST(late_minutes AS DOUBLE) AS late_minutes,
        CAST(net_late_minutes AS DOUBLE) AS net_late_minutes,
        CAST(missing_punch_count AS DOUBLE) AS missing_punch_count,
        overtime_hours
    FROM {{ ref('mart_attendance_kpis') }}
