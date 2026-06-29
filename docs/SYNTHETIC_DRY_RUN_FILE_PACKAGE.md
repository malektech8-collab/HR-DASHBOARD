# Synthetic Dry-Run File Package

This document defines the mock files package used for testing Gate 4 ingestion loop controls.

---

## 1. Safety Rules & Naming Standard

*   **Prefix Requirement**: All employee identifiers, names, and case numbers must use approved synthetic prefixes (e.g. `EMP-SYN-0001`, `Synthetic Employee 001`, `CASE-SYN-0001`).
*   **Opaque candidate keys**: Succession keys must use opaque tokens only (e.g. `SUCC-SYN-0001`). Initials, names, or raw numbers are prohibited.
*   **Folder Restriction**: Files reside exclusively under `data/synthetic_dry_run/input/`. Placing files in `data/real_*` is prohibited.

---

## 2. Ingestion Files Specifications

### 2.1 HRIS / Employee Master
*   **File**: `jisr_employee_master_dryrun.csv`
*   **Columns**: `emp_id`, `emp_num`, `full_name`, `status`, `joining_date`, `nationality`
*   **Valid Rows**: 19
*   **Invalid Rows**: 3 (Missing primary key, duplicate key, invalid date format)

### 2.2 Payroll Details
*   **File**: `netsuite_payroll_ledger_dryrun.xlsx`
*   **Columns**: `netsuite_emp_id`, `pay_period`, `salary_basic`, `gross_salary`, `net_salary`
*   **Valid Rows**: 20
*   **Invalid Rows**: 2 (Negative salary, net pay mismatch)

### 2.3 Attendance
*   **File**: `zk_attendance_logs_dryrun.csv`
*   **Columns**: `badge_emp_id`, `punch_date`, `first_punch_in`, `last_punch_out`
*   **Valid Rows**: 494
*   **Invalid Rows**: 10 (Check-out before check-in, missing date)

### 2.4 Government / Compliance
*   **File**: `gosi_compliance_status_dryrun.csv`
*   **Columns**: `portal_emp_id`, `gosi_active`, `wps_compliance`, `iqama_expiry`
*   **Valid Rows**: 19

### 2.5 Employee Relations
*   **File**: `er_sharepoint_log_dryrun.csv`
*   **Columns**: `sp_case_id`, `sp_subject_emp_id`, `sp_case_category`, `sp_status`
*   **Valid Rows**: 11

### 2.6 Recruitment
*   **File**: `lever_recruitment_reqs_dryrun.csv`
*   **Columns**: `ats_req_id`, `ats_title`, `ats_status`
*   **Valid Rows**: 7

### 2.7 Talent
*   **File**: `successfactors_talent_dryrun.xlsx`
*   **Columns**: `sf_emp_id`, `sf_perf_rating`, `sf_status`
*   **Valid Rows**: 16

### 2.8 Metadata Engine
*   **File**: `command_center_audit_dryrun.csv`
*   **Columns**: `module_key`, `api_health_status`, `reconciliation_status`
*   **Valid Rows**: 9
