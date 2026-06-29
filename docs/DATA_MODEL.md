# Data Model Documentation

This document describes the schema structure of the HR Analytics Command Center.

## Raw Sample Files (`data/sample/`)

### 1. `employees_sample.csv`
Master log of all employees.
- `employee_id` (VARCHAR): Unique employee identifier.
- `employee_name` (VARCHAR): Full name of the employee.
- `nationality` (VARCHAR): Nationality of the employee.
- `is_saudi` (BOOLEAN): Saudi nationality flag.
- `company` (VARCHAR): Subsidiary or company name.
- `department` (VARCHAR): Business department.
- `project` (VARCHAR): Assigned project.
- `job_title` (VARCHAR): Job role designation.
- `job_family` (VARCHAR): Broad category of the job.
- `grade` (VARCHAR): Employee compensation grade.
- `manager_id` (VARCHAR): Employee ID of the manager.
- `cost_center` (VARCHAR): Cost allocation identifier.
- `employment_type` (VARCHAR): Full-time, Part-time, Contractor, etc.
- `contract_type` (VARCHAR): Limited or Unlimited.
- `joining_date` (DATE): Joining date of the employee.
- `termination_date` (DATE): Date of termination (null if active).
- `contract_end_date` (DATE): End date of contract.
- `status` (VARCHAR): Active, Inactive, Terminated, On Leave.
- `basic_salary` (DECIMAL): Base salary.
- `housing_allowance` (DECIMAL): Rent allowance.
- `transport_allowance` (DECIMAL): Commute allowance.

### 2. `payroll_sample.csv`
Monthly payroll record.
- `payroll_period` (VARCHAR): Format YYYY-MM.
- `employee_id` (VARCHAR): Link to employee.
- `basic_salary` (DECIMAL): Paid base salary.
- `housing_allowance` (DECIMAL): Paid housing.
- `transport_allowance` (DECIMAL): Paid transport.
- `other_allowances` (DECIMAL): Extra allowances.
- `overtime_amount` (DECIMAL): Overtime pay.
- `deductions` (DECIMAL): Sum of salary deductions.
- `gross_pay` (DECIMAL): Total salary before deduction.
- `net_pay` (DECIMAL): Gross salary minus deductions.
- `project` (VARCHAR): Project code.
- `cost_center` (VARCHAR): Cost center code.
- `payroll_status` (VARCHAR): Draft, Approved, Paid.

### 3. `attendance_sample.csv`
Daily attendance punch logs.
- `attendance_date` (DATE): Date of log.
- `employee_id` (VARCHAR): Link to employee.
- `shift_name` (VARCHAR): Work shift identifier.
- `scheduled_start` (TIMESTAMP): Expected check-in.
- `scheduled_end` (TIMESTAMP): Expected check-out.
- `actual_check_in` (TIMESTAMP): Real check-in.
- `actual_check_out` (TIMESTAMP): Real check-out.
- `late_minutes` (INTEGER): Calculated delay from scheduled.
- `excused_late_minutes` (INTEGER): Approved late minutes delay.
- `net_late_minutes` (INTEGER): Paid delay (late - excused).
- `absence_days` (DECIMAL): Number of days absent.
- `overtime_hours` (DECIMAL): Overtime worked.
- `overtime_approved` (BOOLEAN): Status of overtime.
- `missing_punch_count` (INTEGER): Incidents of missing check-in/out.
- `project` (VARCHAR): Project code.

### 4. `hr_requests_sample.csv`
Operations requests tickets.
- `request_id` (VARCHAR): Unique ticket number.
- `employee_id` (VARCHAR): Requesting employee.
- `request_type` (VARCHAR): Ticket category (e.g. Leave, Certificate).
- `request_status` (VARCHAR): Open, Closed, In Progress.
- `created_at` (TIMESTAMP): Creation time.
- `closed_at` (TIMESTAMP): Closure time.
- `owner` (VARCHAR): SLA ticket owner.
- `sla_hours` (INTEGER): SLA duration.
- `actual_hours` (INTEGER): Real processing duration.
- `sla_breached` (BOOLEAN): SLA violation indicator.
- `project` (VARCHAR): Project code.

### 5. `compliance_sample.csv`
Saudi compliance indicators.
- `employee_id` (VARCHAR): Link to employee.
- `period` (VARCHAR): Period (YYYY-MM).
- `qiwa_status` (VARCHAR): Qiwa platform contract status.
- `gosi_status` (VARCHAR): GOSI portal registration status.
- `mudad_status` (VARCHAR): Mudad compliance indicator.
- `contract_authenticated` (BOOLEAN): Status of digital authentication.
- `gosi_salary` (DECIMAL): Salary registered in GOSI.
- `payroll_basic_salary` (DECIMAL): Salary in payroll.
- `occupation_code` (VARCHAR): Qiwa occupational code.
- `occupation_match_status` (VARCHAR): Match between contract and real role.
- `work_permit_expiry` (DATE): Expiry of work permit.
- `iqama_expiry` (DATE): Expiry of Iqama (non-Saudis).
- `insurance_status` (VARCHAR): Medical coverage status.

---

## Warehouse Analytical Views (`warehouse/hr_analytics.duckdb`)

### 1. `mart_exec_kpis`
Pre-calculated summary KPI values for the Executive Dashboard.
- `active_headcount` (INTEGER)
- `joiners_count` (INTEGER)
- `leavers_count` (INTEGER)
- `turnover_rate` (FLOAT)
- `payroll_cost` (DECIMAL)
- `overtime_cost` (DECIMAL)
- `absence_days` (DECIMAL)
- `data_quality_score` (FLOAT)

### 2. `mart_exec_trends`
Monthly trend values for Headcount and Payroll.
- `month` (VARCHAR)
- `active_headcount` (INTEGER)
- `payroll_cost` (DECIMAL)

### 3. `mart_data_quality_summary`
Aggregated counts of issues and overall data quality score.
- `data_quality_score` (FLOAT)
- `missing_manager_count` (INTEGER)
- `missing_project_count` (INTEGER)
- `missing_cost_center_count` (INTEGER)
- `missing_nationality_count` (INTEGER)
- `duplicate_employee_count` (INTEGER)
- `invalid_payroll_count` (INTEGER)

### 4. `mart_data_quality_exceptions`
Individual data quality violations list.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `issue_type` (VARCHAR)
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)

### 5. `mart_workforce_kpis`
Pre-calculated summary KPI values for the Workforce Dashboard. Calculates active counts, Saudization rate, and compliance database holes.
- `active_headcount` (INTEGER): Total count of active employees.
- `saudi_headcount` (INTEGER): Count of active Saudi employees.
- `non_saudi_headcount` (INTEGER): Count of active non-Saudi employees.
- `saudization_rate` (FLOAT): Saudi employees divided by active headcount.
- `probation_count` (INTEGER): Active employees joined within the last 90 days.
- `contract_expiring_30` (INTEGER): Active contracts expiring within the next 30 days.
- `iqama_expiring_30` (INTEGER): Active Iqamas expiring within the next 30 days.
- `missing_manager_count` (INTEGER): Count of active employees without a manager.
- `missing_project_count` (INTEGER): Count of active employees without a project.
- `missing_cost_center_count` (INTEGER): Count of active employees without a cost center.

### 6. `mart_workforce_headcount_trend`
Active headcount trend over the last 3 months.
- `month` (VARCHAR): Trend month (YYYY-MM).
- `active_headcount` (INTEGER): Count of active employees.

### 7. `mart_workforce_distribution`
Aggregated counts of headcount across different categorical dimensions (department, project, nationality group, employment status, employment type).
- `category` (VARCHAR): Dimension category name.
- `metric_value` (VARCHAR): Label for dimension value.
- `headcount` (INTEGER): Number of active employees.

### 8. `mart_workforce_contract_expiry`
Contracts expiring aging buckets relative to the current anchor report date.
- `expired` (INTEGER): Count of contracts whose expiry date is in the past.
- `0_30` (INTEGER): Expiry within 0-30 days.
- `31_60` (INTEGER): Expiry within 31-60 days.
- `61_90` (INTEGER): Expiry within 61-90 days.
- `90_plus` (INTEGER): Expiry beyond 90 days.
- `missing_date` (INTEGER): Count of contracts missing expiry dates.

### 9. `mart_workforce_iqama_expiry`
Iqama permit expirations aging buckets relative to the current report date.
- **Data Source**: Joined from the `compliance` table via `employee_id`.
- `expired` (INTEGER): Count of Iqamas whose expiry date is in the past.
- `0_30` (INTEGER): Expiry within 0-30 days.
- `31_60` (INTEGER): Expiry within 31-60 days.
- `61_90` (INTEGER): Expiry within 61-90 days.
- `90_plus` (INTEGER): Expiry beyond 90 days.
- `missing_date` (INTEGER): Count of non-Saudi active employees missing Iqama expiry dates.

### 10. `mart_workforce_exceptions`
Individual data quality and contract risk exceptions list.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `issue_type` (VARCHAR): Type of data issue or contract risk (e.g. Missing Manager, Iqama Expiry Risk, Missing Iqama Expiry Date).
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)

### 11. `base_payroll_current`
Canonical base query representing the current period's payroll records joined to employee attributes.
- `payroll_period` (VARCHAR)
- `employee_id` (VARCHAR)
- `basic_salary` (DECIMAL)
- `housing_allowance` (DECIMAL)
- `transport_allowance` (DECIMAL)
- `other_allowances` (DECIMAL)
- `overtime_amount` (DECIMAL)
- `deductions` (DECIMAL)
- `gross_pay` (DECIMAL)
- `net_pay` (DECIMAL)
- `project` (VARCHAR)
- `cost_center` (VARCHAR)
- `emp_project` (VARCHAR): Standardized project (default: Missing Project).
- `emp_department` (VARCHAR): Standardized department (default: Missing Department).
- `emp_cost_center` (VARCHAR): Standardized cost center (default: Missing Cost Center).
- `emp_status` (VARCHAR): Standardized status (default: Inactive/Terminated/Unknown).
- `employee_name` (VARCHAR)
- `is_saudi` (BOOLEAN)

### 12. `base_payroll_previous`
Canonical base query representing the previous period's payroll records joined to employee attributes. Same schema as `base_payroll_current`.

### 13. `mart_payroll_kpis`
Summary payroll KPIs for the current month.
- `total_payroll_cost` (DECIMAL): Gross payroll total.
- `basic_salary_cost` (DECIMAL): Basic salary total.
- `allowances_cost` (DECIMAL): Sum of housing, transport, and other allowances.
- `overtime_cost` (DECIMAL): Overtime pay total.
- `deductions` (DECIMAL): Total salary deductions.
- `net_payroll` (DECIMAL): Total net payroll paid.
- `avg_cost_per_employee` (DECIMAL): Average total payroll cost per paid employee.
- `payroll_variance_pct` (FLOAT): Percentage MoM cost change.
- `employees_paid` (INTEGER): Unique count of employees paid.
- `payroll_exception_count` (INTEGER): Count of flagged exceptions.

### 14. `mart_payroll_trend`
Historical monthly trend of payroll costs.
- `month` (VARCHAR)
- `total_payroll_cost` (DECIMAL)
- `basic_salary` (DECIMAL)
- `allowances` (DECIMAL)
- `overtime` (DECIMAL)
- `deductions` (DECIMAL)
- `net_payroll` (DECIMAL)
- `headcount` (INTEGER)

### 15. `mart_payroll_by_project`
Payroll cost aggregated by employee assigned project.
- `project` (VARCHAR)
- `headcount` (INTEGER)
- `total_payroll_cost` (DECIMAL)
- `overtime_cost` (DECIMAL)

### 16. `mart_payroll_by_department`
Payroll cost aggregated by employee assigned department.
- `department` (VARCHAR)
- `headcount` (INTEGER)
- `total_payroll_cost` (DECIMAL)
- `overtime_cost` (DECIMAL)

### 17. `mart_payroll_components`
Total cost aggregated by salary component type.
- `component` (VARCHAR)
- `amount` (DECIMAL)

### 18. `mart_payroll_variance_components`
Month-over-month cost variance by salary component.
- `component` (VARCHAR)
- `prev_amount` (DECIMAL)
- `curr_amount` (DECIMAL)
- `change_amount` (DECIMAL)
- `change_pct` (FLOAT)

### 19. `mart_payroll_variance_employees`
Gross pay variance for each employee vs the previous month.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `prev_amount` (DECIMAL)
- `curr_amount` (DECIMAL)
- `change_amount` (DECIMAL)
- `change_pct` (FLOAT)

### 20. `mart_payroll_exceptions`
Flagged data quality, compliance, and calculation exceptions in the payroll run.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `issue_type` (VARCHAR)
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)

### 21. `base_employees_deduplicated`
Deduplicated employee master records representing one authoritative state per employee.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `status` (VARCHAR)
- `department` (VARCHAR)
- `project` (VARCHAR)
- `joining_date` (DATE)
- `termination_date` (DATE)

### 22. `base_attendance_current`
Standardized attendance logs for the current report month with calculated late and net late minutes.
- `attendance_date` (DATE)
- `employee_id` (VARCHAR)
- `calculated_late_minutes` (INTEGER): Lateness beyond grace period rules.
- `calculated_net_late_minutes` (INTEGER): Calculated late minutes minus excused late minutes.
- `record_classification` (VARCHAR): Employee master status mapping.

### 23. `base_expected_attendance`
Dynamically generated expected workdays calendar for active employees, used as the denominator for compliance and absence calculations.
- `calendar_date` (DATE)
- `employee_id` (VARCHAR)
- `absence_days` (DECIMAL): 1.0 if no attendance record or explicitly marked absent, 0.0 otherwise.

### 24. `base_attendance_payroll_overtime`
Employee-level overtime hours from attendance full-joined with overtime costs from payroll.
- `employee_id` (VARCHAR)
- `attendance_ot_hours` (DECIMAL)
- `payroll_ot_cost` (DECIMAL)
- `reconciliation_status` (VARCHAR): Mismatch indicators.

### 25. `mart_attendance_exceptions`
Audit log of flagged attendance exceptions (14 checks including punches, excuse rules, and payroll OT matches).
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `issue_type` (VARCHAR)
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)

### 26. `mart_attendance_kpis`
Summary attendance KPIs for the current month.
- `attendance_compliance_pct` (FLOAT): Completed expected days rate.
- `absence_days` (DECIMAL): Sum of absent days.
- `late_minutes` (INTEGER): Gross calculated late minutes.
- `excused_late_minutes` (INTEGER)
- `net_late_minutes` (INTEGER): Net late minutes.
- `early_leave_minutes` (INTEGER)
- `missing_punch_count` (INTEGER)
- `overtime_hours` (DECIMAL)
- `overtime_cost` (DECIMAL)
- `attendance_exception_count` (INTEGER)

### 27. `mart_attendance_trend`
Three-month trend for attendance KPIs.
- `month` (VARCHAR)
- `attendance_compliance_pct` (FLOAT)
- `absence_days` (DECIMAL)
- `late_minutes` (FLOAT)
- `net_late_minutes` (FLOAT)
- `missing_punch_count` (FLOAT)
- `overtime_hours` (FLOAT)

### 28. `mart_attendance_by_project`
Aggregated compliance, absence, and overtime cost by project.
- `project` (VARCHAR)
- `headcount` (INTEGER)
- `attendance_compliance_pct` (FLOAT)
- `absence_days` (DECIMAL)
- `late_minutes` (INTEGER)
- `missing_punches` (INTEGER)
- `overtime_hours` (DECIMAL)
- `overtime_cost` (DECIMAL)

### 29. `mart_attendance_by_department`
Aggregated compliance, lateness, and overtime cost by department.
- `department` (VARCHAR)
- `headcount` (INTEGER)
- `attendance_compliance_pct` (FLOAT)
- `absence_days` (DECIMAL)
- `late_minutes` (INTEGER)
- `net_late_minutes` (INTEGER)
- `missing_punches` (INTEGER)
- `overtime_hours` (DECIMAL)
- `overtime_cost` (DECIMAL)

### 30. `mart_attendance_late_arrival`
Detailed late arrival incidents and minutes by employee.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `total_late_minutes` (INTEGER)
- `total_excused_minutes` (INTEGER)
- `total_net_late_minutes` (INTEGER)
- `late_arrival_incidents_count` (INTEGER)

### 31. `mart_attendance_overtime`
Individual overtime hours and cost reconciliation status.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `attendance_ot_hours` (DECIMAL)
- `payroll_ot_cost` (DECIMAL)
- `reconciliation_status` (VARCHAR)

### 32. `mart_attendance_missing_punches`
Detailed log of missing punches.
- `employee_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `missing_check_in_count` (INTEGER)
- `missing_check_out_count` (INTEGER)
- `total_missing_punches` (INTEGER)

---

### 33. `employee_relations` (Raw Sample)
Master record log of Employee Relations cases.
- `case_id` (VARCHAR): Business identifier of the case.
- `employee_id` (VARCHAR): Link to subject employee.
- `case_type` (VARCHAR): Disciplinary, Grievance, or Labor Case.
- `case_status` (VARCHAR): Open, In Progress, Pending, Closed.
- `priority` (VARCHAR): High, Medium, Low.
- `created_date` (DATE): Creation date of case.
- `target_due_date` (DATE): Target due date for resolution.
- `closed_date` (DATE): Closure date of case.
- `owner_id` (VARCHAR): Link to investigating employee.
- `escalated` (BOOLEAN): Escalation flag.
- `escalation_reason` (VARCHAR): Reason for escalation.
- `legal_reference` (VARCHAR): Court case or legal reference key.
- `case_number` (VARCHAR): Court case number.
- `description` (VARCHAR): Narrative description of case.

---

## Employee Relations Warehouse Views

### 34. `base_er_cases_current`
ER cases with joined subject employee data.
- `er_case_record_id` (BIGINT): Unique analytical record key.
- `case_id` (VARCHAR): Business identifier.
- `employee_id` (VARCHAR): Subject employee ID.
- `case_type` (VARCHAR)
- `case_status` (VARCHAR)
- `priority` (VARCHAR)
- `created_date` (DATE)
- `target_due_date` (DATE)
- `closed_date` (DATE)
- `owner_id` (VARCHAR)
- `escalated` (BOOLEAN)
- `escalation_reason` (VARCHAR)
- `legal_reference` (VARCHAR)
- `case_number` (VARCHAR)
- `description` (VARCHAR)
- `employee_name` (VARCHAR)
- `project` (VARCHAR)
- `department` (VARCHAR)
- `manager_id` (VARCHAR)
- `company` (VARCHAR)
- `nationality` (VARCHAR)
- `job_title` (VARCHAR)
- `cost_center` (VARCHAR)
- `subject_classification` (VARCHAR)

### 35. `base_er_case_parties`
Resolves status of ER case subject and owner.
- `er_case_record_id` (BIGINT)
- `case_id` (VARCHAR)
- `subject_employee_id` (VARCHAR)
- `subject_employee_name` (VARCHAR)
- `subject_classification` (VARCHAR)
- `owner_employee_id` (VARCHAR)
- `owner_employee_name` (VARCHAR)
- `owner_classification` (VARCHAR)

### 36. `base_hr_requests_current`
Monthly HR Operations requests.
- `request_id` (VARCHAR)
- `employee_id` (VARCHAR)
- `request_type` (VARCHAR)
- `request_status` (VARCHAR)
- `created_at` (TIMESTAMP)
- `closed_at` (TIMESTAMP)
- `owner_id` (VARCHAR)
- `sla_hours` (INTEGER)
- `actual_hours` (INTEGER)
- `sla_breached` (BOOLEAN)
- `project` (VARCHAR)
- `department` (VARCHAR)

### 37. `base_case_sla_clock`
Calculates aging and SLA compliance for ER and HR.
- `source_type` (VARCHAR): 'ER' or 'HR_REQ'.
- `record_id` (VARCHAR)
- `effective_due_date` (DATE)
- `aging_days` (INTEGER)
- `sla_status` (VARCHAR)

### 38. `base_er_case_population`
Comprehensive ER analytical view.
- Joins current cases with SLA clock view.

### 39. `mart_er_exceptions`
Exceptions log for ER cases.
- `case_id` (VARCHAR)
- `employee_name` (VARCHAR)
- `issue_type` (VARCHAR)
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)
- `er_case_record_id` (BIGINT)

### 40. `mart_er_kpis`
Summary KPIs for the ER dashboard.
- `total_open_er_cases` (INTEGER)
- `new_cases_this_month` (INTEGER)
- `closed_cases_this_month` (INTEGER)
- `average_case_aging_days` (FLOAT)
- `overdue_cases` (INTEGER)
- `sla_compliance_pct` (FLOAT)
- `disciplinary_cases` (INTEGER)
- `grievance_cases` (INTEGER)
- `labor_cases` (INTEGER)
- `escalated_cases` (INTEGER)
- `er_exception_count` (INTEGER)

### 41. `mart_er_case_trend`
Simulated and dynamic monthly trend.
- `period` (VARCHAR)
- `new_cases` (INTEGER)
- `closed_cases` (INTEGER)

### 42. `mart_er_cases_by_project`
Caseload and SLA compliance by project.
- `project` (VARCHAR)
- `total_cases` (INTEGER)
- `open_cases` (INTEGER)
- `closed_cases` (INTEGER)
- `escalated_cases` (INTEGER)
- `compliant_cases` (INTEGER)
- `compliance_pct` (FLOAT)

### 43. `mart_er_cases_by_department`
Caseload and SLA compliance by department.
- `department` (VARCHAR)
- `total_cases` (INTEGER)
- `open_cases` (INTEGER)
- `closed_cases` (INTEGER)
- `escalated_cases` (INTEGER)
- `compliant_cases` (INTEGER)
- `compliance_pct` (FLOAT)

### 44. `mart_er_case_type_distribution`
Case type counts.
- `case_type` (VARCHAR)
- `case_count` (INTEGER)

### 45. `mart_er_case_status_distribution`
Case status counts.
- `case_status` (VARCHAR)
- `case_count` (INTEGER)

### 46. `mart_er_sla_performance`
SLA compliance breakdown for ER and HR.
- `category_type` (VARCHAR): 'ER' or 'HR_REQ'.
- `category` (VARCHAR)
- `eligible_count` (INTEGER)
- `compliant_count` (INTEGER)
- `breached_count` (INTEGER)
- `compliance_pct` (FLOAT)

### 47. `mart_er_aging_buckets`
Open cases grouped by age.
- `aging_bucket` (VARCHAR)
- `case_count` (INTEGER)

## Recruitment & Workforce Planning Views (Milestone 2F)

### 48. `base_requisition_source_records`
Raw requisitions source table with generated stable analytical row key and owner mapped to recruiter.
- `requisition_record_id` (BIGINT)
- `requisition_id` (VARCHAR)
- `job_title` (VARCHAR)
- `department` (VARCHAR)
- `project` (VARCHAR)
- `cost_center` (VARCHAR)
- `recruiter_id` (VARCHAR)
- `approval_date` (DATE)
- `target_hire_date` (DATE)
- `closed_date` (DATE)
- `status` (VARCHAR)

### 49. `base_candidate_source_records`
Raw candidates source table with generated stable row key and normalized candidate source.
- `candidate_record_id` (BIGINT)
- `candidate_id` (VARCHAR)
- `candidate_name` (VARCHAR)
- `source` (VARCHAR)
- `raw_source` (VARCHAR)
- `pipeline_stage` (VARCHAR)
- `requisition_id` (VARCHAR)
- `applied_date` (DATE)

### 50. `base_interview_source_records`
Raw interviews table with generated stable row key and standardized interviewer field.
- `interview_record_id` (BIGINT)
- `interview_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `interview_date` (TIMESTAMP)
- `interviewer_id` (VARCHAR)
- `rating` (VARCHAR)
- `outcome` (VARCHAR)

### 51. `base_offer_source_records`
Raw offers table with generated stable row key and standardized status field.
- `offer_record_id` (BIGINT)
- `offer_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `offer_date` (DATE)
- `salary` (DOUBLE)
- `offer_status` (VARCHAR)
- `outcome_date` (DATE)

### 52. `base_onboarding_source_records`
Raw onboarding table with generated stable row key and standardized hire date.
- `onboarding_record_id` (BIGINT)
- `onboarding_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `hire_date` (DATE)
- `status` (VARCHAR)
- `employee_id` (VARCHAR)

### 53. `base_recruitment_requisitions_current`
Canonical active requisitions population for the report month with calculated effective target hire dates.
- `requisition_record_id` (BIGINT)
- `requisition_id` (VARCHAR)
- `job_title` (VARCHAR)
- `department` (VARCHAR)
- `project` (VARCHAR)
- `cost_center` (VARCHAR)
- `recruiter_id` (VARCHAR)
- `approval_date` (DATE)
- `target_hire_date` (DATE)
- `closed_date` (DATE)
- `status` (VARCHAR)
- `effective_target_hire_date` (DATE)

### 54. `base_candidate_canonical`
Deduplicated authoritative candidate records using the latest application record by applied date.
- `candidate_record_id` (BIGINT)
- `candidate_id` (VARCHAR)
- `candidate_name` (VARCHAR)
- `source` (VARCHAR)
- `raw_source` (VARCHAR)
- `pipeline_stage` (VARCHAR)
- `requisition_id` (VARCHAR)
- `applied_date` (DATE)

### 55. `base_candidate_pipeline_current`
Candidates associated with current requisitions up to the report month end.
- `candidate_record_id` (BIGINT)
- `candidate_id` (VARCHAR)
- `candidate_name` (VARCHAR)
- `source` (VARCHAR)
- `pipeline_stage` (VARCHAR)
- `requisition_id` (VARCHAR)
- `applied_date` (DATE)

### 56. `base_interview_activity_current`
Interviews scheduled in the current report month.
- `interview_record_id` (BIGINT)
- `interview_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `interview_date` (TIMESTAMP)
- `interviewer_id` (VARCHAR)
- `rating` (VARCHAR)
- `outcome` (VARCHAR)

### 57. `base_offer_activity_current`
Offers extended in the current report month.
- `offer_record_id` (BIGINT)
- `offer_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `offer_date` (DATE)
- `salary` (DOUBLE)
- `offer_status` (VARCHAR)
- `outcome_date` (DATE)

### 58. `base_onboarding_current`
Onboardings starting in the current report month.
- `onboarding_record_id` (BIGINT)
- `onboarding_id` (VARCHAR)
- `candidate_id` (VARCHAR)
- `hire_date` (DATE)
- `status` (VARCHAR)
- `employee_id` (VARCHAR)

### 59. `base_workforce_plan_current`
Headcount targets for the report month.
- `period` (VARCHAR)
- `project` (VARCHAR)
- `department` (VARCHAR)
- `planned_headcount` (INTEGER)

### 60. `base_vacancy_population`
Vacancy requests approved on or before the report month end.
- `request_id` (VARCHAR)
- `department` (VARCHAR)
- `project` (VARCHAR)
- `job_title` (VARCHAR)
- `quantity` (INTEGER)
- `status` (VARCHAR)
- `approved_date` (DATE)

### 61. `mart_recruitment_exceptions`
Flagged recruitment violations.
- `record_id_str` (VARCHAR)
- `issue_type` (VARCHAR)
- `description` (VARCHAR)
- `severity` (VARCHAR)
- `recommended_action` (VARCHAR)

### 62. `mart_recruitment_kpis`
KPI card summary values.
- `open_requisitions` (BIGINT)
- `approved_vacancies` (DECIMAL)
- `candidates_in_pipeline` (BIGINT)
- `interviews_scheduled` (BIGINT)
- `offers_extended` (BIGINT)
- `offer_acceptance_pct` (DOUBLE)
- `hires_this_month` (BIGINT)
- `average_time_to_fill` (DOUBLE)
- `overdue_requisitions` (BIGINT)
- `workforce_plan_fulfillment_pct` (DOUBLE)
- `recruitment_exception_count` (BIGINT)

### 63. `mart_recruitment_pipeline`
funnel count breakdown.
- `pipeline_stage` (VARCHAR)
- `candidate_count` (INTEGER)

### 64. `mart_recruitment_trends`
Simulated trend metrics.
- `period` (VARCHAR)
- `requisitions_opened` (BIGINT)
- `hires` (BIGINT)

### 65. `mart_recruitment_by_project`
Requisitions status by project.
- `project` (VARCHAR)
- `total_requisitions` (INTEGER)
- `open_requisitions` (INTEGER)
- `closed_requisitions` (INTEGER)
- `overdue_requisitions` (INTEGER)

### 66. `mart_recruitment_by_department`
Requisitions status by department.
- `department` (VARCHAR)
- `total_requisitions` (INTEGER)
- `open_requisitions` (INTEGER)
- `closed_requisitions` (INTEGER)
- `overdue_requisitions` (INTEGER)

### 67. `mart_recruitment_time_to_fill`
Average days to fill by project/department.
- `department` (VARCHAR)
- `project` (VARCHAR)
- `average_time_to_fill` (DOUBLE)
- `hire_count` (INTEGER)

### 68. `mart_recruitment_source_effectiveness`
Candidate counts and hire conversions by sourcing source.
- `source` (VARCHAR)
- `candidate_count` (INTEGER)
- `hire_count` (INTEGER)
- `conversion_pct` (DOUBLE)

### 69. `mart_offer_acceptance`
Offer status distribution.
- `offer_status` (VARCHAR)
- `offer_count` (INTEGER)

### 70. `mart_onboarding_status`
Onboarding status distribution.
- `onboarding_status` (VARCHAR)
- `hire_count` (INTEGER)

### 71. `mart_workforce_plan_vs_actual`
Workforce plan vs actual active headcount comparisons.
- `project` (VARCHAR)
- `department` (VARCHAR)
- `planned_headcount` (INTEGER)
- `actual_headcount` (INTEGER)
- `fulfillment_pct` (DOUBLE)


