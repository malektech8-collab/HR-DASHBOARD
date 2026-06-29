# HR Command Center — Source-to-Dashboard Lineage Template

This document provides the lineage mapping from raw input files down to frontend dashboard metrics, linking file inputs to synthetic contracts and mapping Data Stewards to RBAC keys.

---

## 1. Lineage Mapping Table

| Source System | Inbound File | Contract Reference | Base Table | DuckDB View | Mart View | API Endpoint | Frontend Page | Visual / KPI Affected | Data Steward | RBAC Role Key | Validation Frequency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `src_hris_employee` | `jisr_emp.csv` | [Employee Master Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `employees` | `base_workforce` | `mart_workforce_kpis` | `/api/workforce/summary` | `/workforce` | Active Headcount | **HR Operations Administrator** | `hr_operations_manager` | Daily |
| `src_payroll_netsuite` | `ledger.xlsx` | [Payroll Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `payroll` | `base_payroll` | `mart_payroll_kpis` | `/api/payroll/summary` | `/payroll` | Total Payroll Cost | **Payroll Manager** | `payroll_manager` | Monthly |
| `src_attendance` | `punches.csv` | [Attendance Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `attendance` | `base_attendance` | `mart_attendance_kpis` | `/api/attendance/summary` | `/attendance` | Late Arrival Minutes | **Attendance Clerk** | `hr_operations_manager` | Daily |
| `src_gov_compliance` | `gosi.csv` | [Compliance Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `compliance` | `base_compliance` | `mart_compliance_kpis` | `/api/compliance/summary` | `/compliance` | Saudization Rate % | **Compliance Manager** | `compliance_manager` | Weekly |
| `src_er_case_tracker` | `er_log.csv` | [ER Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `er_cases` | `base_er` | `mart_er_kpis` | `/api/er/summary` | `/er` | Active Legal Cases | **ER Coordinator** | `employee_relations_manager` | Daily |
| `src_recruitment_ats` | `ats.csv` | [Recruitment Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `recruitment` | `base_recruitment` | `mart_recruitment_kpis` | `/api/recruitment/summary` | `/recruitment` | Open Requisitions | **Recruitment Coordinator** | `recruitment_manager` | Daily |
| `src_talent_lms` | `reviews.xlsx` | [Talent Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `reviews` | `base_talent` | `mart_talent_kpis` | `/api/talent/summary` | `/talent` | Review Completion % | **L&D Coordinator** | `talent_manager` | Weekly |
| `src_metadata_engine` | `audit.csv` | [Metadata Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `audit_log` | `base_command_center` | `mart_command_center_overview` | `/api/command-center/summary` | `/command-center` | Overview QA Status | **Data Quality Engineer** | `admin_system` | Daily |

---

## 2. Lineage Audit Rules
*   Data Stewards must verify that all DuckDB views correctly implement the column mappings specified in [REAL_DATA_FIELD_MAPPING.md](file:///c:/tmp/HR-DASHBOARD/docs/REAL_DATA_FIELD_MAPPING.md).
*   Any mismatches between the source file schema and the Base Table must trigger automatic file quarantine.

---

## 3. Real Data Security Lineage
During Gate 5 operations, real-data lineage columns are linked to the signed-off owner matrices in [REAL_DATA_ACCESS_SIGNOFF_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/REAL_DATA_ACCESS_SIGNOFF_PACKAGE.md) to ensure row-level access permissions are aligned.
