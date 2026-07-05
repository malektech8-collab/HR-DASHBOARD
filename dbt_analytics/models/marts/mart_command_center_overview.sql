{{ config(materialized='view') }}

SELECT * FROM command_center_overview_data
