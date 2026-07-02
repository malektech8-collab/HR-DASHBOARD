# Release Candidate Package: v0.1.1-synthetic-governance-rc

## Overview
This release candidate (`v0.1.1-synthetic-governance-rc`) represents a stabilized, fully local-sandbox build of the HR Analytics Command Center. The primary focus of this release is testing and validating the **Synthetic Data Simulation Engine** and the **Governance Lock System**.

## Package Contents
1. **Synthetic Data Engine**: Simulates HR profiles, payroll activities, and department metrics without pulling any real employee records.
2. **Governance Widget UI**: The frontend control panel showing the current state of governance approvals.
3. **DuckDB Warehouse Schema**: Localized analytical database built for sandbox telemetry testing.
4. **Local Validation Suite**: Automated checks verifying that the synthetic generators and constraints function correctly.

## Strict Sandbox Configuration
* **No Real-Data Readiness**: All systems are hardcoded to isolate the database from actual production networks.
* **Governance Locks Default to Hold**: By default, all key authorization switches default to **Hold** / **Not Approved**. There is no programmatic way to override these gates to connect to real endpoints in this release.
* **Network Isolation**: All analytical queries execute solely on the local DuckDB file instance (`data/hr_analytics_sandbox.db`).
