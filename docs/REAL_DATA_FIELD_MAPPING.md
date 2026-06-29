# HR Command Center — Real Data Field Mapping Contract

This document acts as the technical contract mapping inbound file columns to target canonical fields. Every mapping is subject to the validation protocols registered in [SOURCE_MAPPING_VALIDATION_PROTOCOL.md](file:///c:/tmp/HR-DASHBOARD/docs/SOURCE_MAPPING_VALIDATION_PROTOCOL.md).

---

## 1. Field Mapping Grid

| Source Category | Source System | Contract Reference | Source Column | Canonical Column | Required | Data Type | Transformation Rule | Privacy Class | Masking Rule | Exception ID |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **Employee Master** | `src_hris_employee` | [Employee Master Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `emp_id` | `employee_id` | Yes | `VARCHAR` | `TRIM(emp_id)` | Personal Data (PII) | None (Internal PK) | None |
| **Employee Master** | `src_hris_employee` | [Employee Master Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `full_name` | `employee_name` | Yes | `VARCHAR` | `INITCAP(full_name)` | Personal Data (PII) | Pseudonymize (Initials + ID) | None |
| **Payroll** | `src_payroll_netsuite` | [Payroll Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `gross_salary` | `gross_pay` | Yes | `DECIMAL(18,2)` | Float cast | Financial Sensitive | Access Restricted / Masked | None |
| **Payroll** | `src_payroll_netsuite` | [Payroll Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `net_salary` | `net_pay` | Yes | `DECIMAL(18,2)` | Float cast | Financial Sensitive | Access Restricted / Masked | None |
| **Payroll** | `src_payroll_netsuite` | [Payroll Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `total_deductions` | `deductions` | Yes | `DECIMAL(18,2)` | Float cast | Financial Sensitive | Access Restricted / Masked | [EXP-002](file:///c:/tmp/HR-DASHBOARD/docs/GATE_2_MAPPING_EXCEPTION_REGISTER.md) |
| **Attendance** | `src_attendance_biometric` | [Attendance Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `first_punch_in` | `actual_check_in` | Yes | `TIMESTAMP` | Timestamp cast | Operational Data | None | None |
| **Government / Compliance** | `src_gov_compliance` | [Compliance Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `national_id` | `national_id_number` | Yes | `VARCHAR` | String parse | Govt ID Sensitive | Partial Mask (`*****1234`) | None |
| **Employee Relations** | `src_er_case_tracker` | [ER Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `sp_case_category` | `case_type` | Yes | `VARCHAR` | None | Operational Data | None | None |
| **Recruitment** | `src_recruitment_ats` | [Recruitment Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `req_id` | `requisition_id` | Yes | `VARCHAR` | Trim, uppercase | Internal | None | None |
| **Talent & Succession** | `src_talent_lms` | [Talent Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `sf_perf_rating` | `rating` | Yes | `INTEGER` | Integer cast | Personal Sensitive | Access Restricted | None |
| **Talent & Succession** | `src_talent_lms` | [Talent Contract](file:///c:/tmp/HR-DASHBOARD/config/synthetic_test_file_contracts.yml) | `sf_successor_emp_id` | `successor_employee_key` | Yes | `VARCHAR` | Opaque token (e.g. `SUCC-0001`) | Personal Sensitive | Opaque Token Masking | [EXP-001](file:///c:/tmp/HR-DASHBOARD/docs/GATE_2_MAPPING_EXCEPTION_REGISTER.md) |

---

## 2. General Mapping and Integration Guidelines
*   **Verification**: All mapping rows must be verified by their respective technical and business owners prior to Gate 1 signoff, following the [GATE_1_APPROVAL_WORKFLOW.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_1_APPROVAL_WORKFLOW.md).
*   **Change Control**: If a source column schema changes, a formal change request must be submitted to the Data Steward to update this document and the underlying YAML parsing configurations.
*   **Security Compliance**: Privacy classifications must match [PRIVACY_AND_MASKING_POLICY.md](file:///c:/tmp/HR-DASHBOARD/docs/PRIVACY_AND_MASKING_POLICY.md) strictly.
