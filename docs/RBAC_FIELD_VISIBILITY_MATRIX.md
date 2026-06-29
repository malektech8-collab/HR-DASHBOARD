# RBAC & Field Visibility Matrix

This document maps role-based visibility controls and module access levels for the analytical command center.

---

## 1. Role Module Access Registry

| Role Key | Allowed Modules | Drilldown | Salary | Deductions | ER Cases | Talent rating | Govt ID |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`admin_system`** | All (`*`) | Yes | Yes | Yes | Yes | Yes | Masked |
| **`hr_executive`** | All (`*`) | Yes | Yes | Yes | Yes | Yes | Masked |
| **`hr_operations_manager`** | Exec, DQ, WF, Attendance, Compliance | Yes | No | No | No | Yes | Masked |
| **`payroll_manager`** | Exec, Payroll | Yes | Yes | Yes | No | No | Masked |
| **`employee_relations_manager`** | Exec, ER | Yes | No | No | Yes | No | Masked |
| **`recruitment_manager`** | Exec, Recruitment | Yes | No | No | No | No | Hidden |
| **`talent_manager`** | Exec, Talent | Yes | No | No | No | Yes | Hidden |
| **`compliance_manager`** | Exec, Compliance | Yes | No | No | No | No | Masked |
| **`project_manager`** | Workforce, Attendance | No | No | No | No | No | Hidden |
| **`viewer_executive_aggregate_only`** | Executive | No | No | No | No | No | Hidden |
| **`auditor_read_only`** | All (`*`) | Yes | Yes | Yes | Yes | Yes | Masked |

---

## 2. Field-Level Visibility Definitions
*   **Hidden**: Field is entirely omitted from database queries and UI components for the role.
*   **Aggregate Only**: Values can only be consumed in department/project SUM or AVG metrics. Row-level visibility is blocked.
*   **Masking**: Data is partially redacted (e.g. Iqamas as `1098******`, mobile numbers as `+966*****5678`).
*   **Pseudonymized**: Identifiers are replaced with deterministic opaque keys (e.g. successor employee key as `SUCC-0001`). Initials, employee numbers, and raw IDs are hidden.
*   **Full Access**: Raw, unmasked values are displayed to authorized roles.
