{{ config(materialized='view') }}

-- 1. Active employee missing GOSI status (conditional on GOSI source availability)
    SELECT employee_id, employee_name, 'Missing GOSI Status Record' AS issue_type, 
           'Active employee has no record in GOSI registration field' AS description, 
           'Critical' AS severity, 'Check GOSI enrollment status' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE gosi_status IS NULL AND {{ var('has_gosi_source_sql') }}
    
    UNION ALL
    
    -- 2. Active employee not registered in GOSI, if status exists
    SELECT employee_id, employee_name, 'Not Registered in GOSI' AS issue_type, 
           'Active employee exists but status is ' || gosi_status AS description, 
           'Critical' AS severity, 'Register employee in GOSI portal' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE gosi_status IS NOT NULL AND gosi_status != 'Registered'
    
    UNION ALL
    
    -- 3. Active employee missing WPS record (conditional on WPS source availability)
    SELECT employee_id, employee_name, 'Missing WPS Record' AS issue_type, 
           'Active employee has no record in WPS (Mudad) portal' AS description, 
           'Critical' AS severity, 'Add employee to WPS {{ ref('stg_payroll') }} files' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE mudad_status IS NULL AND {{ var('has_wps_source_sql') }}
    
    UNION ALL
    
    -- 4. Employee appearing in WPS but inactive in workforce (only when WPS status exists)
    SELECT employee_id, employee_name, 'WPS Record for Inactive Employee' AS issue_type, 
           'Employee is appearing in government WPS file with status ' || mudad_status || ' but is inactive/terminated (' || COALESCE(employee_status, 'Unknown') || ')' AS description, 
           'Critical' AS severity, 'Stop WPS {{ ref('stg_payroll') }} entry and verify status' AS recommended_action 
    FROM {{ ref('base_government_platform_records') }} 
    WHERE record_classification != 'Active Employee' AND mudad_status IS NOT NULL
    
    UNION ALL
    
    -- 5. Missing project for {{ ref('stg_compliance') }} population
    SELECT employee_id, employee_name, 'Missing Project assignment' AS issue_type, 
           'Active employee is missing project code assignment' AS description, 
           'Warning' AS severity, 'Update project mapping in master file' AS recommended_action 
    FROM {{ ref('base_active_workforce') }} 
    WHERE project IS NULL OR TRIM(project) = ''
    
    UNION ALL
    
    -- 6. Missing department for {{ ref('stg_compliance') }} population
    SELECT employee_id, employee_name, 'Missing Department assignment' AS issue_type, 
           'Active employee is missing department mapping' AS description, 
           'Warning' AS severity, 'Update department mapping in master file' AS recommended_action 
    FROM {{ ref('base_active_workforce') }} 
    WHERE department IS NULL OR TRIM(department) = ''
    
    UNION ALL
    
    -- 7. Missing cost center for {{ ref('stg_compliance') }} population
    SELECT employee_id, employee_name, 'Missing Cost Center assignment' AS issue_type, 
           'Active employee is missing cost center assignment' AS description, 
           'Warning' AS severity, 'Update cost center in master file' AS recommended_action 
    FROM {{ ref('base_active_workforce') }} 
    WHERE cost_center IS NULL OR TRIM(cost_center) = ''
    
    UNION ALL
    
    -- 8. Missing Qiwa Contract
    SELECT employee_id, employee_name, 'Missing Qiwa Contract' AS issue_type, 
           'Active employee has no contract registered in Qiwa' AS description, 
           'Critical' AS severity, 'Register digital contract in Qiwa portal' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE qiwa_status IS NULL OR qiwa_status != 'Active'
    
    UNION ALL
    
    -- 9. Contract Not Authenticated
    SELECT employee_id, employee_name, 'Contract Not Authenticated' AS issue_type, 
           'Digital contract is pending employee authentication' AS description, 
           'Warning' AS severity, 'Request employee to log into Qiwa and approve contract' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE contract_authenticated = FALSE
    
    UNION ALL
    
    -- 10. GOSI Salary Mismatch (excluding nulls)
    SELECT employee_id, employee_name, 'GOSI Salary Mismatch' AS issue_type, 
           'Registered GOSI salary (' || gosi_salary || ') differs from basic salary (' || payroll_basic_salary || ')' AS description, 
           'Critical' AS severity, 'Update GOSI salary records to match {{ ref('stg_payroll') }} basic' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE gosi_salary IS NOT NULL AND payroll_basic_salary IS NOT NULL AND gosi_salary != payroll_basic_salary
    
    UNION ALL
    
    -- 11. Missing Salary Values in Compliance/Payroll
    SELECT employee_id, employee_name, 'Missing Salary Info' AS issue_type, 
           'Active employee has null salary values in GOSI or {{ ref('stg_payroll') }} base' AS description, 
           'Warning' AS severity, 'Update salary values in GOSI/{{ ref('stg_payroll') }} database' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE gosi_salary IS NULL OR payroll_basic_salary IS NULL
    
    UNION ALL
    
    -- 12. Occupation Mismatch
    SELECT employee_id, employee_name, 'Occupation Mismatch' AS issue_type, 
           'Qiwa occupational code does not match active role description' AS description, 
           'Warning' AS severity, 'Correct occupational designation code in Qiwa portal' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE occupation_match_status IS NULL OR occupation_match_status != 'Matched'
    
    UNION ALL
    
    -- 13. Insurance Inactive
    SELECT employee_id, employee_name, 'Insurance Inactive' AS issue_type, 
           'Medical insurance coverage status is not active' AS description, 
           'Critical' AS severity, 'Activate insurance profile in provider database' AS recommended_action 
    FROM {{ ref('base_compliance_current') }} 
    WHERE insurance_status IS NULL OR insurance_status != 'Active'
    
    UNION ALL
    
    -- 14. Missing Nationality / Saudi Status
    SELECT employee_id, employee_name, 'Missing Nationality' AS issue_type, 
           'Active employee has null/missing nationality or Saudization status' AS description, 
           'Warning' AS severity, 'Update employee nationality records in master file' AS recommended_action 
    FROM {{ ref('base_active_workforce') }} 
    WHERE nationality IS NULL OR TRIM(nationality) = '' OR is_saudi IS NULL
    
    UNION ALL
    
    -- 15. Non-Saudi employee missing Iqama expiry date
    SELECT employee_id, employee_name, 'Missing Iqama Expiry Date' AS issue_type, 
           'Non-Saudi employee is missing an Iqama expiry date' AS description, 
           'Warning' AS severity, 'Update {{ ref('stg_compliance') }} records with Iqama expiry date' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE iqama_bucket = 'missing_date'
    
    UNION ALL
    
    -- 16. Non-Saudi employee with expired Iqama
    SELECT employee_id, employee_name, 'Expired Iqama' AS issue_type, 
           'Iqama has expired: ' || COALESCE(CAST(iqama_expiry AS VARCHAR), 'N/A') AS description, 
           'Critical' AS severity, 'Renew Iqama immediately' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE iqama_bucket = 'expired'
    
    UNION ALL
    
    -- 17. Non-Saudi employee with Iqama expiring within 30 days
    SELECT employee_id, employee_name, 'Iqama Expiring Soon' AS issue_type, 
           'Iqama is expiring within 30 days: ' || COALESCE(CAST(iqama_expiry AS VARCHAR), 'N/A') AS description, 
           'Warning' AS severity, 'Initiate Iqama renewal' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE iqama_bucket = '0_30'
    
    UNION ALL
    
    -- 18. Non-Saudi employee missing work permit expiry date
    SELECT employee_id, employee_name, 'Missing Work Permit Expiry Date' AS issue_type, 
           'Non-Saudi employee is missing a Work Permit expiry date' AS description, 
           'Warning' AS severity, 'Update {{ ref('stg_compliance') }} records with Work Permit expiry date' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE work_permit_bucket = 'missing_date'
    
    UNION ALL
    
    -- 19. Non-Saudi employee with expired work permit
    SELECT employee_id, employee_name, 'Expired Work Permit' AS issue_type, 
           'Work permit has expired: ' || COALESCE(CAST(work_permit_expiry AS VARCHAR), 'N/A') AS description, 
           'Critical' AS severity, 'Renew work permit immediately' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE work_permit_bucket = 'expired'
    
    UNION ALL
    
    -- 20. Non-Saudi employee with work permit expiring within 30 days
    SELECT employee_id, employee_name, 'Work Permit Expiring Soon' AS issue_type, 
           'Work permit is expiring within 30 days: ' || COALESCE(CAST(work_permit_expiry AS VARCHAR), 'N/A') AS description, 
           'Warning' AS severity, 'Initiate work permit renewal' AS recommended_action 
    FROM {{ ref('base_document_expiry') }} 
    WHERE work_permit_bucket = '0_30'
