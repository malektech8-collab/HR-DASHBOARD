# Gate 1 Risk Register

This document tracks all identified risks, impacts, mitigations, and target resolution timelines before moving to active data integration.

---

## 1. Risk Matrix & Definitions

Risk severity is computed as:
$$\text{Severity} = \text{Impact} \times \text{Likelihood}$$

*   **Impact Score**: 1 (Insignificant) to 5 (Critical)
*   **Likelihood Score**: 1 (Rare) to 5 (Almost Certain)
*   **Severity Rating**:
    *   **High**: 15–25
    *   **Medium**: 8–12
    *   **Low**: 1–6

---

## 2. Active Risk Register

| Risk ID | Source Category | Risk Type | Risk Description | Impact | Likelihood | Severity | Owner | Mitigation Action | Target Resolution | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :--- |
| **RSK-001** | Talent | Missing Owner | Talent & Development Director has not signed off on data ownership. | 4 | 3 | High (12) | HR Systems Lead | Schedule briefing to clarify duties and obtain signoff. | 2026-07-10 | Awaiting Owner |
| **RSK-002** | Payroll | Sensitive Field | Salary component details lack approved masking rules from legal. | 5 | 2 | High (10) | Finance Director | Enforce strict column-level database masking (redacting names and Iqamas) until signed off. | 2026-07-05 | Mitigation Planned |
| **RSK-003** | Attendance | Manual Dependency | Biometric clock data requires manual export to CSV by the clerk. | 3 | 4 | Medium (12) | HR Operations Manager | Configure direct automated SFTP push from the Teco server to `data/real_inbox/`. | 2026-07-25 | Mitigation Planned |
| **RSK-004** | Compliance | Conflicting Truth | Saudization statistics might conflict between external GOSI reports and active payroll. | 3 | 3 | Medium (9) | Gov Relations Officer | Establish GOSI registry status as the primary legal source of truth. | 2026-07-15 | Open |
| **RSK-005** | Talent | Unmapped Required Field | Successor employee ID mappings are in draft state pending legal classification. | 4 | 2 | Medium (8) | Talent & Dev Director | Work with data steward to document the schema and map to sf_successor_emp_id. | 2026-07-20 | Open |
| **RSK-006** | ER | Legal/Privacy Risk | Case descriptions may contain raw names or sensitive investigation details. | 5 | 4 | High (20) | ER Manager | Run regex-based redaction parser on the description field at ingestion stage. | 2026-07-08 | Mitigation Planned |

---

## 3. Critical Blockers

Any risk with a Severity $\ge$ 15 or status `Blocked` is classified as a critical blocker. Currently:
*   **RSK-006 (Employee Relations Legal/Privacy Risk)** is marked as a critical blocker. No real ER files can be processed until the regex parser is implemented and tested.
