# Final Ingestion Authorization Requirements

This document outlines the strict parameters required for written authorization approvals prior to starting a pilot real-data load.

---

## 1. Approval Criteria

*   **Format**: Sign-off must be written and logged as an official PDF in `docs/approvals/`.
*   **Exact Scope**: Approval must reference the specific source system (`Metadata Audit Engine`), files, columns, and date ranges.
*   **Fields Mapped**: Ingestion is prohibited if any unmapped columns or missing privacy classifications exist in configurations.
*   **Security Controls**: CISO must sign off on the active AES-256 folder storage and audit logging schema validations.
*   **Expiration**: Approvals expire exactly 7 days after issue. Re-authorization is required if load windows miss.

---

## 2. Authorization Package Reference
For details on active requests and sign-off statuses, refer to [FINAL_WRITTEN_AUTHORIZATION_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/FINAL_WRITTEN_AUTHORIZATION_PACKAGE.md).
