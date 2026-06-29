# Synthetic Test File Ingestion Contract

This document acts as the quality contract defining schemas, formats, and validation rules for synthetic test data files drops.

---

## 1. Safety Controls and Rules

*   **Real Data Prohibition**: The `real_data_allowed` parameter is enforced as **`false`** across all files. No real employee records or live system connection keys may be drops.
*   **Target Ingestion**: All synthetic test files must drop in `data/real_inbox/` with names matching the regex naming convention.
*   **Staging Isolation**: Real-data landing folders remain completely clean except for their `.gitkeep` placeholders.
*   **Privacy Integrations**: Inbound schemas are linked to classifications defined in [privacy_classification.yml](file:///c:/tmp/HR-DASHBOARD/config/privacy_classification.yml). Sensitive fields must map to masking rules.
*   **Dry-Run Alignment**: Schemas are validated using dry-run files configured in [synthetic_dry_run_manifest.yml](file:///c:/tmp/HR-DASHBOARD/config/synthetic_dry_run_manifest.yml).

---

## 2. Source Ingestion Specifications

### 2.1 File Characteristics
*   **Delimiter**: Comma (`,`) for CSV files; sheet selections for Excel (XLSX) spreadsheets.
*   **Encoding**: UTF-8.
*   **Row-Level Constraints**: Empty lines or null key IDs will trigger automated quarantine rules.

### 2.2 Category Parameters

| Source Category | File Pattern (Regex) | Format | Required Key Field | Expected Row Count | Contract Status |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **Employee Master** | `^jisr_employee_master_\d{8}\.csv$` | CSV | `emp_id` | 19 | Approved |
| **Payroll** | `^netsuite_payroll_ledger_\d{6}\.xlsx$` | XLSX | `netsuite_emp_id` | 20 | Approved |
| **Attendance** | `^zk_attendance_logs_\d{8}\.csv$` | CSV | `badge_emp_id` | 494 | Approved |
| **Compliance** | `^gosi_compliance_status_\d{8}\.csv$` | CSV | `portal_emp_id` | 19 | Approved |
| **Employee Relations** | `^er_sharepoint_log_\d{8}\.csv$` | CSV | `sp_case_id` | 11 | Approved |
| **Recruitment** | `^lever_recruitment_reqs_\d{8}\.csv$` | CSV | `ats_req_id` | 7 | Approved |
| **Talent & Succession** | `^successfactors_talent_\d{8}\.xlsx$` | XLSX | `sf_emp_id` | 16 | Approved |
| **Metadata Engine** | `^command_center_audit_\d{8}\.csv$` | CSV | `module_key` | 9 | Approved |
