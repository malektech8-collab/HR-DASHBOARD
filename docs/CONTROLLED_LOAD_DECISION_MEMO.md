# Controlled Load Decision Memo

This memo outlines the recommended first-load domain selection and operational decision status.

---

## 1. Domain Recommendations

To minimize data leakage risk during initial pipeline validations, the steering committee enforces the following boundaries:

*   **Metadata / Data Quality Engine**: **`Recommended`**
    *   *Rationale*: Contains zero employee identity records, compensation details, or compliance metrics. Safest choice.
*   **HRIS Employee Master**: **`Conditionally Recommended`**
    *   *Rationale*: Allowed only with minimal pseudonymized fields (e.g. employee IDs masked). Names, emails, and Iqamas must be redacted.
*   **Payroll & Compensation**: **`Not Recommended`**
    *   *Rationale*: High risk of salary leak. Prohibited in first controlled load.
*   **Employee Relations (ER)**: **`Not Recommended`**
    *   *Rationale*: High risk of exposing sensitive legal narratives. Prohibited in first controlled load.
*   **Talent & Performance**: **`Not Recommended`**
    *   *Rationale*: Potential succession leak. Prohibited in first controlled load.

---

## 2. Ingestion Status
*   **Gate 5 Status**: **`Conditional Go`**
*   *Prerequisites*: Requires explicit written sign-off from the CHRO before load scheduling can close. Refer to [CONTROLLED_LOAD_SCHEDULING_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/CONTROLLED_LOAD_SCHEDULING_PACKAGE.md).
