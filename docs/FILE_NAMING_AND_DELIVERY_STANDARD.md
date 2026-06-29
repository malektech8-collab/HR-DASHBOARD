# File Naming and Delivery Standard

This document details the naming patterns and delivery folder targets required for all ingestion files.

---

## 1. Directory Structure

Ingestion staging utilizes the following folder structure to process files:

*   **`data/real_inbox/`**: The secure landing zone for SFTP drops.
*   **`data/real_quarantine/`**: Isolation folder for files with validation failures.
*   **`data/real_approved/`**: Validated files ready for DuckDB view generation.
*   **`data/real_rejected/`**: Unapproved files rejected during staging.
*   **`data/real_archive/`**: Archive location for fully processed files.

---

## 2. File Pattern Specifications

| Ingestion Category | Expected Regex Pattern | Delivery Location | Fail Action |
| :--- | :--- | :--- | :--- |
| **Employee Master** | `^jisr_employee_master_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |
| **Payroll** | `^netsuite_payroll_ledger_\d{6}\.xlsx$` | `data/real_inbox/` | Move to Quarantine |
| **Attendance** | `^zk_attendance_logs_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |
| **Compliance** | `^gosi_compliance_status_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |
| **Employee Relations** | `^er_sharepoint_log_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |
| **Recruitment** | `^lever_recruitment_reqs_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |
| **Talent & Succession** | `^successfactors_talent_\d{8}\.xlsx$` | `data/real_inbox/` | Move to Quarantine |
| **Metadata Engine** | `^command_center_audit_\d{8}\.csv$` | `data/real_inbox/` | Move to Quarantine |

---

## 3. General Validation Protocol

If a file fails to match its expected regex pattern, the scheduler moves the file to `data/real_quarantine/` and logs an exception warning in the Metadata module.

---

## 4. Dry-Run Folder Isolation
During Gate 4 validation, all mock synthetic ingestion processes route files strictly under `data/synthetic_dry_run/` directories.
