# Real Data Access Signoff Package

This package maps the active role authorizations required for accessing live dashboard modules during pilot operations.

---

## 1. Role Authorization Registry

*   **Role**: `admin_system`
    *   **Modules**: All (`*`)
    *   **Level**: Row-level
    *   **Salaries**: Yes
    *   **ER cases**: Yes
    *   **Gov IDs**: Masked
    *   **Status**: Approved
    *   **Approver**: CISO

*   **Role**: `hr_executive`
    *   **Modules**: All (`*`)
    *   **Level**: Row-level
    *   **Salaries**: Yes
    *   **ER cases**: Yes
    *   **Gov IDs**: Masked
    *   **Status**: Approved
    *   **Approver**: VP of HR Operations

*   **Role**: `payroll_manager`
    *   **Modules**: `payroll`
    *   **Level**: Row-level
    *   **Salaries**: Yes
    *   **ER cases**: No
    *   **Gov IDs**: Masked
    *   **Status**: Approved
    *   **Approver**: Finance Director

*   **Role**: `employee_relations_manager`
    *   **Modules**: `er`
    *   **Level**: Row-level
    *   **Salaries**: No
    *   **ER cases**: Yes
    *   **Gov IDs**: Masked
    *   **Status**: Approved
    *   **Approver**: VP of HR Operations
