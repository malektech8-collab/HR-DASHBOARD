# Privacy & Security Risk Register

This register details the privacy, security, and access-control risks identified during the integration planning phase, alongside their mitigation plans.

---

## 1. Risk Matrix

### RSK-SEC-001: Excessive Access to Salary & ER Data
*   **Risk Category**: Excessive Access
*   **Description**: Non-HR managers accessing sensitive row-level salaries or employee relations cases.
*   **Affected Fields**: `basic_salary`, `disciplinary_cases_description`
*   **Affected Modules**: `payroll`, `er`
*   **Impact Rating**: High
*   **Security Impact**: High
*   **Likelihood**: 2 (Low)
*   **Severity**: 15 (High)
*   **Owner**: Information Security Lead
*   **Mitigation**: Block non-HR roles from entering the Payroll and ER modules using access control filters.
*   **Status**: Mitigation Planned

### RSK-SEC-002: Re-identification Risk in Small Groups
*   **Risk Category**: Re-identification Risk
*   **Description**: Individual identities derived from small demographic groups (e.g. nationality/gender) in project statistics.
*   **Affected Fields**: `nationality`, `gender`
*   **Affected Modules**: `workforce`, `compliance`
*   **Impact Rating**: Medium
*   **Security Impact**: Low
*   **Likelihood**: 3 (Medium)
*   **Severity**: 12 (Medium)
*   **Owner**: Data Privacy Officer
*   **Mitigation**: Implement a minimum sample size check to suppress demographic categories with counts $\le$ 5.
*   **Status**: Accepted

### RSK-SEC-003: Salary Leakage in UI Drilldowns
*   **Risk Category**: Salary Leakage
*   **Description**: UI drilldown lists exposing individual salaries.
*   **Affected Fields**: `gross_salary`, `net_salary`
*   **Affected Modules**: `payroll`
*   **Impact Rating**: High
*   **Security Impact**: High
*   **Likelihood**: 2 (Low)
*   **Severity**: 16 (High)
*   **Owner**: Information Security Lead
*   **Mitigation**: Restrict row-level detail listings to payroll-authorized roles only; general users view aggregates only.
*   **Status**: Mitigation Planned

### RSK-SEC-004: Successor Identity Leakage
*   **Risk Category**: Successor Identity Exposure
*   **Description**: Access to raw successor employee IDs or names.
*   **Affected Fields**: `successor_employee_key`
*   **Affected Modules**: `talent`
*   **Impact Rating**: Critical
*   **Security Impact**: High
*   **Likelihood**: 2 (Low)
*   **Severity**: 18 (Critical)
*   **Owner**: Data Privacy Officer
*   **Mitigation**: Enforce opaque successor candidate key hashing (e.g. `SUCC-0001` or salted hashes). Raw details never stored or displayed.
*   **Status**: Resolved
