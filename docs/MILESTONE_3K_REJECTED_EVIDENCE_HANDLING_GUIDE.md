# Milestone 3K - Rejected Evidence Handling Guide

Synthetic evidence is rejected when it violates the Milestone 3K schema or governance rules.

## Rejection Reasons

- Missing required fields
- Wrong evidence ID
- Wrong signatory role
- Restricted source category
- Attempted approval of real-data execution
- Attempted load scheduling
- Stop criteria count mismatch
- Restricted fields present
- Unsafe input path

## Decision Impact

Rejected synthetic evidence keeps the decision recommendation at `Hold`. It does not approve real evidence, execution, scheduling, communications, or Go/No-Go outcomes.
