# Gate 1 Source Owner Signoff

This document registers the readiness scorecards and signoff summaries required to move from Gate 0 (Mock Data Development) to Gate 1 (Source Inventory Approved) status.

---

## 1. Gate 1 Readiness scoring Model

The project utilizes a formal scorecard to compute readiness before any real data is accepted for ingestion:

*   **Source Owner Assigned (15%)**: A business owner role is formally assigned to the source category.
*   **Technical Owner Assigned (10%)**: A technical engineer is assigned to maintain integration feeds.
*   **Data Steward Assigned (15%)**: A data steward is assigned to perform validation checks.
*   **Source Format Documented (10%)**: The source file layout (CSV, XLSX, XML) is documented.
*   **Delivery Method Documented (10%)**: SFTP, API, or local upload method is configured.
*   **Refresh Frequency Documented (10%)**: Expected latency (daily, weekly, monthly) is set.
*   **Required Fields Mapped/Exceptioned (15%)**: Canonical fields map to source fields or exceptions.
*   **Privacy Classification Complete (10%)**: All source fields have clear privacy levels.
*   **Open Critical Risks Resolved/Accepted (5%)**: Zero unmitigated critical risks remain.

### Score Thresholds
*   **Ready**: Score $\ge$ 90% and zero critical blockers.
*   **Conditional**: Score 70–89% or non-critical gaps remain.
*   **Not Ready**: Score < 70% or any critical blocker remains.

---

## 2. Ingestion Category Scorecard

| Source Category | Business Owner | Tech Owner | Data Steward | Score | Gate 1 Status |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Employee Master** | HR Director | IT Lead | HR Admin | 95% | **Ready** |
| **Payroll** | Finance Director | ERP Admin | Payroll Manager | 75% | **Conditional** (Blocked on Masking Approval) |
| **Attendance** | HR Ops Manager | Network Eng | Attendance Clerk | 95% | **Ready** |
| **Compliance** | Gov Relations | G2B Architect | Compliance Mgr | 85% | **Conditional** (PII classification review) |
| **Employee Relations** | ER Manager | SharePoint Admin | ER Coordinator | 80% | **Conditional** (Pending text-scrub checks) |
| **Recruitment** | Talent Head | ATS Engineer | Recruitment Coord | 100% | **Ready** |
| **Talent & Succession** | T&D Director | LMS Lead | L&D Coordinator | 50% | **Not Ready** (Missing owners & schemas) |
| **Metadata Engine** | HR Systems Lead | Antigravity Arch | Data Quality Eng | 100% | **Ready** |

---

## 3. Approval Mandate

No real employee data files will be loaded into the ingestion engine until all categories move to **Ready** or **Conditional** status (with signed-off mitigations) and Gate 1 is officially closed.
