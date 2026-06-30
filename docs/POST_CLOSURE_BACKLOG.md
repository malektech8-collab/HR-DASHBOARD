# Post-Closure Backlog

## Overview

This backlog tracks architectural cleanups, test framework upgrades, and validation improvements scheduled for execution after the initial development phase is closed.

## Backlog Items

### 1. Refactor Test Suite Framework
- **Status**: CLOSED/RESOLVED
- **Description**: Migrate legacy tests from live localhost HTTP calls to FastAPI's mock client.
- **Priority**: High (Fixes pytest execution).

### 2. Standardize Component Interfaces
- **Status**: CLOSED/RESOLVED
- **Description**: Fix type definitions and prop structures of `<KpiCard />` and `<ExceptionTable />` across frontend modules to resolve TypeScript compile errors.
- **Priority**: High (Restores `npm run build` success).

### 3. CommandCenter Variable and console.debug Cleanup
- **Status**: CLOSED/RESOLVED
- **Description**: Clean up the unused `navStatus` variable and verbose console.debug statements in `CommandCenter.tsx`.
- **Priority**: Medium (Build hygiene & noise reduction).

### 4. Implement Automated Secrets Monitoring
- **Description**: Deploy Git pre-commit hooks to scan files automatically for credentials, passwords, and `.env` additions.
- **Priority**: Medium.

### 5. Advanced Audit Logging
- **Description**: Expand backend endpoints to log all configuration file reads and write events for traceability.
- **Priority**: Low.
