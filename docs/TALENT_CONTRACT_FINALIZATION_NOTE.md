# Talent Ingestion Contract Finalization Note

This note documents the final parameters applied to the Talent / Performance / Learning synthetic test contract to transition it to Approved status.

---

## 1. Safety & Privacy Enforcements

*   **Real Data Check**: Enforces `real_data_allowed: false` across all file parse parameters.
*   **Successor Identity**: Handled strictly via pseudonymous opaque key mapping (`successor_employee_key`). No names, initials, or raw employee numbers are allowed in raw or view schemas.
*   **Ratings Sensitivity**: Performance ratings are classified as Confidential; dashboards summarize ratings in aggregate, and row-level views are restricted to managers and Talent leads.
*   **Flight Risk Restricted**: Flight risk flags are restricted to executive roles.
*   **Readiness Values**: Controlled to list values (`Ready Now`, `1-2 Years`, `3-5 Years`).
