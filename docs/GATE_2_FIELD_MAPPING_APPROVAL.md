# Gate 2 Field Mapping Approval

This document outlines the validation criteria, progress scorecards, and signoff statuses required to transition data mapping specifications from draft status to approved status.

---

## 1. Gate 2 Readiness Scorecard

To close Gate 2, every ingestion category must be mapped to target views or have approved exceptions:

| Ingestion Category | Required Target Fields | Mapped Fields | Exceptioned Fields | Steward Signoff | Owner Signoff | Gate 2 Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Employee Master** | 13 | 13 | 0 | Checked | Checked | **Ready** |
| **Payroll** | 10 | 9 | 1 | Checked | Checked | **Ready** |
| **Attendance** | 10 | 10 | 0 | Checked | Checked | **Ready** |
| **Compliance** | 7 | 7 | 0 | Checked | Checked | **Ready** |
| **Employee Relations** | 9 | 9 | 0 | Checked | Checked | **Ready** |
| **Recruitment** | 10 | 10 | 0 | Checked | Checked | **Ready** |
| **Talent & Succession** | 10 | 8 | 2 | Checked | Checked | **Ready** |
| **Metadata Engine** | 9 | 9 | 0 | Checked | Checked | **Ready** |

---

## 2. Gate 2 Transition Rules

*   **Ready**: 100% of required fields mapped or exceptioned, and both Steward and Owner approvals recorded.
*   **Conditional**: Non-critical mapping items or clarifications remain under active work.
*   **Not Ready**: Gaps exist on required primary keys, or missing privacy classifications.

No live pilot ingestion can be scheduled until all categories achieve **Ready** status.
