{{ config(materialized='view') }}

SELECT * FROM {{ ref('stg_training_catalog') }}
