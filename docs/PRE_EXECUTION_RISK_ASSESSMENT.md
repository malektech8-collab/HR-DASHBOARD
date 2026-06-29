# Pre-Execution Risk Assessment

This assessment logs potential risks, mitigation strategies, and decision impacts immediately prior to starting pilot loads.

---

## 1. Risk Matrix

### RSK-PRE-001: File Delivery Delays
*   **Description**: Inbound files not dropped during scheduled off-peak window.
*   **Severity**: Medium | **Likelihood**: Medium
*   **Mitigation**: Fallback window scheduled 24 hours later.
*   **Decision Impact**: Conditional Go | **Status**: Mitigated

### RSK-PRE-002: Unexpected Schema Changes
*   **Description**: Unmapped fields or missing column headers in drop file.
*   **Severity**: High | **Likelihood**: Low
*   **Mitigation**: Auto-reject validation rules; move file to rejected folder.
*   **Decision Impact**: No-Go | **Status**: Mitigated

### RSK-PRE-003: Sensitive Columns Included Outside Scope
*   **Description**: Raw payroll, ER case detail, or IBAN columns dropped in input folder.
*   **Severity**: Critical | **Likelihood**: Low
*   **Mitigation**: Immediate disk sector wipe; reject file transfer.
*   **Decision Impact**: No-Go | **Status**: Mitigated

### RSK-PRE-004: Backup Snapshot Rollback Failure
*   **Description**: Pre-load database recovery fails during mock restore run.
*   **Severity**: High | **Likelihood**: Low
*   **Mitigation**: Validate backup restoration path before starting import window.
*   **Decision Impact**: No-Go | **Status**: Mitigated

---

## 2. Stop Criteria Reference
For details on technical detection methods and owners, refer to [CONTROLLED_LOAD_EXECUTION_STOP_CRITERIA.md](file:///c:/tmp/HR-DASHBOARD/docs/CONTROLLED_LOAD_EXECUTION_STOP_CRITERIA.md).
