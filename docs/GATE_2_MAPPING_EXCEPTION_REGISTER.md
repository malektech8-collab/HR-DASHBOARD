# Gate 2 Mapping Exception Register

This document registers the deviations, justifications, and planned resolutions for fields that cannot be mapped in the current integration phase.

---

## 1. Exception Registry

### EXP-001: Succession Plan - Successor Employee Key
*   **Source Category**: Talent / Performance / Learning
*   **Canonical Table**: `base_succession_plans`
*   **Canonical Field**: `successor_employee_key`
*   **Exception Type**: Privacy Review Pending
*   **Reason**: Successor identity exposure requires high-level data clearance.
*   **Impact Rating**: High
*   **Privacy Impact**: Critical PII
*   **Business Owner**: Talent & Development Director
*   **Data Steward**: L&D Coordinator
*   **Approval Status**: Approved - Resolved with Opaque Key
*   **Mitigation Action**: Use opaque successor key (e.g., SUCC-0001) in DB and restrict dashboards to aggregate-only for standard users.
*   **Target Resolution**: 2026-06-29

### EXP-002: Payroll Deductions Mismatch
*   **Source Category**: Payroll
*   **Canonical Table**: `base_payroll_records`
*   **Canonical Field**: `deductions`
*   **Exception Type**: Source Owner Clarification Required
*   **Reason**: Awaiting clarification from NetSuite administrator regarding GOSI pension contribution flags.
*   **Impact Rating**: Medium
*   **Privacy Impact**: Financial Sensitive
*   **Business Owner**: Finance Director
*   **Data Steward**: Payroll Manager
*   **Approval Status**: Approved - Resolved with Aggregate Deductions
*   **Mitigation Action**: Map deductions as a single aggregate numeric canonical field. Detailed lines out of scope.
*   **Target Resolution**: 2026-06-29
