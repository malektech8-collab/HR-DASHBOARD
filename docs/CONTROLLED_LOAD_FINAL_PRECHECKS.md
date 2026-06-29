# Controlled Load Final Prechecks

This document defines the checks executed exactly 1 hour prior to opening the scheduling load window.

---

## 1. Final Pre-Load Verification

*   [ ] **Staging Directories Empty**: Confirm target paths in `data/real_*` contain only `.gitkeep`.
*   [ ] **Written Token Present**: Check for CHRO and CISO written safety tokens in register.
*   [ ] **Staging Partition Encrypted**: Confirm AES-256 loopback drives are mounted.
*   [ ] **Audit Log Trigger**: Confirm logger database connection responds.
*   [ ] **Pre-load Database Backup**: Re-verify pre-load DuckDB snapshot exists on backup volume.
*   [ ] **Execution & Rollback Owners Available**: Confirm on-call team responds via ping.
*   [ ] **Stop Criteria Active**: Verify the 22 stop criteria configurations are parsed.

---

## Milestone 3I Cross-Reference

The Go/No-Go decision is a mandatory pre-check dependency. Final prechecks cannot proceed until the decision is upgraded from Hold.

- [Go/No-Go Decision Record](CONTROLLED_LOAD_GO_NO_GO_DECISION_RECORD.md)
- [Final Scope Confirmation](FINAL_SCOPE_CONFIRMATION.md)
