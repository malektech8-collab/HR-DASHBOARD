# Milestone 3J - Evidence Validation Rules

Milestone 3J defines evidence validation planning rules only.

## Validation Rules

| Rule ID | Rule | Failure Action |
|---------|------|----------------|
| 3J-VAL-001 | Evidence must map to AUTH-EVD-001, AUTH-EVD-002, or AUTH-EVD-003 | Reject evidence |
| 3J-VAL-002 | Evidence must identify the correct signatory role | Reject evidence |
| 3J-VAL-003 | Evidence must reference `Data Quality / Command Center Metadata` only | Reject evidence |
| 3J-VAL-004 | Evidence must not include real HR employee records or restricted fields | Reject evidence and keep Hold |
| 3J-VAL-005 | Evidence must not include credentials, tokens, API keys, passwords, database URLs, or production connection strings | Reject evidence and escalate to security reviewer |
| 3J-VAL-006 | Evidence must confirm all 22 stop criteria remain active | Keep Hold until corrected |
| 3J-VAL-007 | Evidence must not approve actual real-data execution | Reject evidence |
| 3J-VAL-008 | Evidence must not schedule a load window | Reject evidence |

## Allowed Evidence Statuses

- Not Provided
- Provided - Pending Review
- Valid
- Valid with Conditions
- Rejected
- Expired

## Current Result

All evidence remains `Not Provided`; therefore, the decision recommendation remains `Hold`.
