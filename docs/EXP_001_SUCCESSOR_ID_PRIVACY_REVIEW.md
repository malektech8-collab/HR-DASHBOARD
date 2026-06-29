# Privacy Impact Review — EXP-001 Successor Employee Reference

This document provides the formal privacy impact assessment for successor identifiers under the approved opaque token treatment.

---

## 1. Privacy Impact Assessment

*   **Identifiability Risk**: Raw successor identifiers (employee IDs or names) present high re-identification risks to sensitive succession planning.
*   **Resolution Strategy**: Apply deterministic opaque token masking (e.g. mapping `EMP-0020` to `SUCC-0001`).
*   **Initials and Numbers**: Initials, employee numbers, and raw IDs are strictly prohibited from display.
*   **Opaque Token Definition**: Salted, non-reversible deterministic tokens represent the only allowed row-level identifiers.
*   **Access Controls**: Access to row-level opaque successor lists is restricted to authorized Talent executives only. Standard users view succession data at the aggregate level.
*   **Re-identification Map**: Stored in a separate security database outside the analytics platform, requiring independent access audits.
