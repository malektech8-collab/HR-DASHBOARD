# Source Mapping Validation Protocol

This document establishes the validation checks that every source-to-canonical data mapping must pass before transitioning to Gate 2 approval.

---

## 1. Core Field Validation Rules

For each field in a source file, the Data Steward must validate the following parameters:

1.  **Source Field Exists**: The field must be present in the raw export schema.
2.  **Data Type Matches**: Raw values must parse into the declared SQL type (e.g. `VARCHAR`, `DATE`, `DECIMAL`).
3.  **Transformation Rule Declared**: Transformation expressions must use standard SQL (e.g. `COALESCE`, `CASE WHEN`).
4.  **Privacy Classification Assigned**: The field must be classified (e.g. Personal Data, Financial Sensitive, Legal Sensitive).
5.  **Masking Rule Specified**: Sensitive fields must map to a masking method in the masking policy.
6.  **Owner Validation Status Set**: The Business Owner must verify the field mapping definition.

---

## 2. Ingestion-Level Verifications

### 2.1 File Naming Checks
*   All inbound files must match the regex naming conventions configured in [file_naming_standards.yml](file:///c:/tmp/HR-DASHBOARD/config/file_naming_standards.yml).
*   Any mismatches must immediately prevent import, sending the raw file to `data/real_quarantine/`.

### 2.2 Control Totals Audits
*   The system must calculate and assert control totals (headcounts, gross salary sums, attendance ranges) specified in [source_control_totals.yml](file:///c:/tmp/HR-DASHBOARD/config/source_control_totals.yml).
*   Any variance outside of the expected thresholds must block ingestion and generate high-priority quality exceptions.

---

## 3. Domain Target Checklist

### 3.1 Employee Master
*   `employee_id` (Primary Key, unique)
*   `employee_number` (Business identifier)
*   `employee_name` (Requires name-pseudonymization masking)
*   `status`, `joining_date`, `termination_date`, `company`, `department`, `project`, `cost_center`, `job_title`, `nationality`, `manager_id`

### 3.2 Payroll
*   `employee_id`, `payroll_period`, `basic_salary`, `housing_allowance`, `transport_allowance`, `other_allowance`, `overtime_amount`, `deductions` (Aggregate amount only; detailed categories out of scope), `gross_pay`, `net_pay`

### 3.3 Attendance
*   `employee_id`, `attendance_date`, `scheduled_start`, `scheduled_end`, `actual_check_in`, `actual_check_out`, `late_minutes`, `excused_late_minutes`, `overtime_hours`, `absence_flag`

### 3.4 Compliance
*   `employee_id`, `gosi_status`, `wps_status`, `qiwa_contract_status`, `iqama_expiry_date`, `work_permit_expiry_date`, `insurance_status`

### 3.5 Employee Relations
*   `case_id`, `subject_employee_id`, `case_owner_id`, `case_type`, `case_status`, `created_date`, `target_due_date`, `closed_date`, `escalation_flag`

### 3.6 Recruitment
*   `requisition_id`, `job_title`, `department`, `project`, `approval_date`, `target_hire_date`, `status`, `recruiter_id`, `candidate_id`, `pipeline_stage`

### 3.7 Talent
*   `employee_id`, `review_period`, `rating`, `review_status`, `reviewer_id`, `goal_status`, `course_id`, `learning_status`, `successor_employee_key` (Requires opaque pseudonymous token; raw identity re-identification map held separately), `readiness`
