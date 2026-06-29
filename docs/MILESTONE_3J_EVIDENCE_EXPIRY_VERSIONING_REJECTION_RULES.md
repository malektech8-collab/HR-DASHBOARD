# Milestone 3J - Evidence Expiry, Versioning, and Rejection Rules

This document defines planning rules for future evidence lifecycle management.

## Expiry Rules

| Rule | Value |
|------|-------|
| Default evidence validity window | 30 days |
| Expired evidence status | Expired |
| Expired evidence decision impact | Keep decision recommendation Hold |
| Refresh requirement | New evidence version must be submitted and validated |

## Versioning Rules

| Rule | Value |
|------|-------|
| Version format | AUTH-EVD-###-vN |
| Initial version default | v1 |
| Superseded evidence retained | Yes |
| Default version status | Not Provided |
| Decision impact recorded per version | Yes |

## Rejection Rules

Evidence must be rejected when it:

- References a domain other than `Data Quality / Command Center Metadata`.
- Contains real HR employee records.
- Contains restricted fields.
- Contains credentials, tokens, API keys, passwords, database URLs, or production connection strings.
- Attempts to approve real-data execution.
- Attempts to schedule a load window.
- Claims an actual Go/No-Go meeting outcome.

Rejected evidence keeps the decision recommendation at `Hold`.
