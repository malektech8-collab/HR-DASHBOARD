SELECT * FROM {{ source('hr_raw', 'data_quality') }}
