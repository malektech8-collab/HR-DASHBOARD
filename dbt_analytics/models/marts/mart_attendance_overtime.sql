{{ config(materialized='view') }}

SELECT * FROM {{ ref('base_attendance_payroll_overtime') }}
