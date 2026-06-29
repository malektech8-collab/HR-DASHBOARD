# HR Command Center — Real Data Go/No-Go Criteria

This document lists the strict technical, legal, and operational gates required to transition the command center from synthetic-only mode to pilot real-data ingestion.

---

## 1. Gate 1 Readiness Score Thresholds (Go/No-Go)
1.  **Readiness Score Target**: Ingestion categories must achieve a minimum readiness score of **90%** based on the scoring model defined in [GATE_1_SOURCE_OWNER_SIGNOFF.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_1_SOURCE_OWNER_SIGNOFF.md).
2.  **Critical Blockers**: There must be **zero critical blockers** (defined as open risks with a Severity $\ge$ 15, or marked as Blocked in the risk register).
3.  **Owner Verification**: All Business Owners, Technical Owners, and Data Stewards must sign off on their respective categories using the templates in [GATE_1_SIGNOFF_TEMPLATE.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_1_SIGNOFF_TEMPLATE.md).

---

## 2. Gate 2 Mapping Readiness Thresholds (Go/No-Go)
1.  **Field Mapping Integrity**: **100%** of required canonical fields must be mapped to raw columns or have formal, approved exceptions logged in [GATE_2_MAPPING_EXCEPTION_REGISTER.md](file:///c:/tmp/HR-DASHBOARD/docs/GATE_2_MAPPING_EXCEPTION_REGISTER.md).
2.  **Exception Status**: All exceptions must have a status of **Resolved** or **Approved** (Go/No-Go: `Go` requires no active Conditional exceptions).
3.  **Synthetic Contracts**: All 8 categories must have approved synthetic test-file contracts in place prior to active testing.

---

## 3. Gate 3 Security & Access Thresholds (Go/No-Go)
1.  **Masking Coverage**: **100%** of fields classified as sensitive must have assigned and verified masking rules (Go/No-Go: `Go` requires verified masking configuration).
2.  **Opaque Candidate Keys**: Candidate identities in succession tables must utilize opaque tokens (e.g. `SUCC-0001` or salted deterministic hashes). Names, initials, or employee IDs are prohibited (Go/No-Go: `Go` requires verified successor key pseudonymization).
3.  **Open Risks**: Risk Register must contain **zero open/unaccepted security risks** (Go/No-Go: `Go` requires all security risks to be marked Mitigated, Accepted, or Resolved).
4.  **Audit Logs & Retention**: Logging events and retention policies must be signed off by CISO and Legal.

---

## 4. Gate 4 Synthetic Dry-Run Thresholds (Go/No-Go)
1.  **Dry-Run Loop Status**: **100%** of dry-run file ingest checks must pass for valid files, and fail correctly for invalid files (Go/No-Go: `Go` requires all 8 categories verified).
2.  **No-Real-Data Audit**: Audit script must execute with zero PII/IBAN patterns detected in the input package (Go/No-Go: `Go` requires verified clean dry-run manifest).
3.  **Control Totals Match**: Checksum verification calculations must reconcile with zero variance.

---

## 5. Gate 5 Controlled Load Readiness Decision (Go/No-Go)
1.  **Decision Status**: Ingestion scheduling requires the Gate 5 status to be formally registered as `Go for Controlled Load Scheduling` or `Conditional Go` (Go/No-Go: `Go` requires no active No-Go blockers in the decision log).
2.  **Pre-Execution Checklist**: 100% of pre-execution parameters must be verified.
3.  **Risk Register status**: Zero unmitigated risks in pre-execution assessment.

---

## 6. Gate 5 Final Written Authorization (Go/No-Go)
1.  **Written Sign-off**: Ingestion execution requires the Gate 5 written authorization status to be set to **`Approved`** in [FINAL_WRITTEN_AUTHORIZATION_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/FINAL_WRITTEN_AUTHORIZATION_PACKAGE.md). (Go/No-Go: `Go` requires written sign-off from both CISO and CHRO).
2.  **Expiry**: Approval date must be within 7 days of ingestion execution window.
3.  **Stop Criteria**: Zero active stop conditions from the 22 stop criteria.

---

## Milestone 3I Cross-Reference

The formal Go/No-Go decision record and meeting pack for the controlled load are prepared in Milestone 3I.

- [Go/No-Go Decision Record](CONTROLLED_LOAD_GO_NO_GO_DECISION_RECORD.md)
- [Go/No-Go Meeting Pack](CONTROLLED_LOAD_GO_NO_GO_MEETING_PACK.md)
- [Final Authorization Evidence Review](FINAL_AUTHORIZATION_EVIDENCE_REVIEW.md)
