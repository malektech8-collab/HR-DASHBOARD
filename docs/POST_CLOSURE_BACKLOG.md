# Post-Closure Backlog

## Overview

This backlog tracks architectural cleanups, test framework upgrades, and validation improvements scheduled for execution after the initial development phase is closed.

## Backlog Items

### 1. Refactor Test Suite Framework
- **Description**: Migrate legacy tests from live localhost HTTP calls to FastAPI's mock client.
- **Priority**: High (Fixes pytest execution).

### 2. Standardize Component Interfaces
- **Description**: Fix type definitions and prop structures of `<KpiCard />` and `<ExceptionTable />` across frontend modules to resolve TypeScript compile errors.
- **Priority**: High (Restores `npm run build` success).

### 3. Implement Automated Secrets Monitoring
- **Description**: Deploy Git pre-commit hooks to scan files automatically for credentials, passwords, and `.env` additions.
- **Priority**: Medium.

### 4. Advanced Audit Logging
- **Description**: Expand backend endpoints to log all configuration file reads and write events for traceability.
- **Priority**: Low.
