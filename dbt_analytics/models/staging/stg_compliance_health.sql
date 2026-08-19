-- One platform, one source. See data/contracts/compliance_health_schema.yml
-- for why `compliance` is four contracts rather than one.
SELECT * FROM {{ source('hr_raw', 'compliance_health') }}
