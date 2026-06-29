# Source Owner Responsibility Matrix

This document defines the roles, duties, and signoff criteria for managing real data ingestion streams in the HR Command Center.

---

## 1. Role Definitions

### 1.1 Business Owner
The individual accountable for the business processes that generate the source data.
*   **Key Responsibilities**:
    *   Approve the field-level mappings to canonical targets.
    *   Validate that data reflects real-world operations.
    *   Sign off on privacy classifications.
*   **Deliverable**: Final approval of the data mapping schema.

### 1.2 Technical Owner
The system administrator or engineer responsible for the source software, server, database, or export flow.
*   **Key Responsibilities**:
    *   Maintain automated scheduled file drops to `data/real_inbox/`.
    *   Ensure file formats match configuration placeholders.
    *   Provide technical support for integration troubleshooting.
*   **Deliverable**: Secure connection configuration and export automation.

### 1.3 Data Steward
The data specialist responsible for validating schema structures and checking for compliance.
*   **Key Responsibilities**:
    *   Validate data types and transformation rules.
    *   Monitor data quality checks and resolve validation failures.
    *   Assess field-level privacy and security controls.
*   **Deliverable**: Mapping validation reports and daily quality signoffs.

---

## 2. Ingestion Responsibility Matrix (RACI)

| Ingestion Category | Business Owner | Technical Owner | Data Steward | Accountable Executive |
| :--- | :--- | :--- | :--- | :--- |
| **Employee Master** | HR Director (A) | IT Lead (R) | HR Admin (R) | VP of HR |
| **Payroll** | Finance Director (A) | ERP Admin (R) | Payroll Manager (R) | CFO |
| **Attendance** | HR Ops Manager (A) | Network Eng (R) | Attendance Clerk (R) | HR Director |
| **Compliance** | Gov Relations (A) | G2B Architect (R) | Compliance Mgr (R) | VP of HR |
| **Employee Relations** | ER Manager (A) | SharePoint Admin (R) | ER Coordinator (R) | HR Director |
| **Recruitment** | Talent Head (A) | ATS Engineer (R) | Recruitment Coord (R)| VP of HR |
| **Talent & Succession** | T&D Director (A) | LMS Lead (R) | L&D Coordinator (R) | VP of HR |
| **Metadata Engine** | HR Systems Lead (A) | Antigravity Arch (R) | Data Quality Eng (R) | VP of HR |

---

## 3. Operational Obligations

Every change to a source database schema requires a minimum **5 working days notice** to the Data Steward to allow updating configuration files and preventing downstream ingestion failures.
