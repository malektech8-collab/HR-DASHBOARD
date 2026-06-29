# Controlled Load Execution Stop Criteria

This document lists the 22 mandatory stop criteria that must immediately halt execution if triggered.

---

## 1. Stop Criteria Count: 22

1.  **STP-001: Real data outside approved folder**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Systems Architect
2.  **STP-002: Unauthorized field appears**
    *   *Severity*: High | *Action*: Halt pipeline | *Owner*: Data Quality Steward
3.  **STP-003: Payroll field appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
4.  **STP-004: Government ID appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
5.  **STP-005: Bank/IBAN appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
6.  **STP-006: ER/legal field appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
7.  **STP-007: Talent/performance field appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
8.  **STP-008: Free-text employee note appears**
    *   *Severity*: High | *Action*: Halt pipeline | *Owner*: Data Quality Steward
9.  **STP-009: Credential or token appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Security Lead
10. **STP-010: Live connection string appears**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Security Lead
11. **STP-011: File name does not match approved pattern**
    *   *Severity*: Medium | *Action*: Reject drop file | *Owner*: Data Quality Steward
12. **STP-012: Record count exceeds approved range**
    *   *Severity*: Medium | *Action*: Reject drop file | *Owner*: Data Quality Steward
13. **STP-013: Control total mismatch exceeds tolerance**
    *   *Severity*: High | *Action*: Halt pipeline | *Owner*: Data Quality Steward
14. **STP-014: Masking rule fails**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
15. **STP-015: Access restriction fails**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Security Lead
16. **STP-016: Audit logging fails**
    *   *Severity*: High | *Action*: Halt pipeline | *Owner*: Systems Architect
17. **STP-017: Dashboard exposes restricted fields**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Data Privacy Officer
18. **STP-018: Source owner withdraws approval**
    *   *Severity*: High | *Action*: Halt pipeline | *Owner*: Systems Architect
19. **STP-019: Privacy/security owner issues stop order**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Systems Architect
20. **STP-020: Rollback owner is unavailable**
    *   *Severity*: High | *Action*: Abort window | *Owner*: IT Operations Director
21. **STP-021: Incident response owner is unavailable**
    *   *Severity*: High | *Action*: Abort window | *Owner*: IT Operations Director
22. **STP-022: Staging disk encryption is disabled or fails**
    *   *Severity*: Critical | *Action*: Halt pipeline | *Owner*: Security Lead

---

## Milestone 3I Cross-Reference

All 22 stop criteria are confirmed intact in the Milestone 3I Stop Criteria Confirmation review.

- [Stop Criteria Confirmation](STOP_CRITERIA_CONFIRMATION.md)
- [Go/No-Go Meeting Pack](CONTROLLED_LOAD_GO_NO_GO_MEETING_PACK.md)
