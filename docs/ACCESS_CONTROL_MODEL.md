# HR Command Center — Access Control Model

This document outlines the role-based permission matrix for the analytical command center.

## 1. System Role Definitions
- **`admin_system`**: Full admin access, database refreshes, and access management.
- **`hr_executive`**: View all metrics (executive and employee level), approve data intake gates.
- **`hr_operations_manager`**: Core operations visibility, excluding salaries and legal case details.
- **`payroll_manager`**: Exclusive operational owner of the Payroll & Cost sub-system.
- **`employee_relations_manager`**: Exclusive operational owner of ER cases and SLA tracking.
- **`recruitment_manager`**: Oversees hiring pipeline, manpower planning, and sourcing metrics.
- **`talent_manager`**: Core owner of Performance reviews, succession pipelines, and LMS stats.
- **`compliance_manager`**: Core owner of Saudization compliance, WPS registries, and expiries.
- **`project_manager`**: Read-only aggregated project views, zero salary/personnel details.
- **`viewer_executive_aggregate_only`**: View main executive high-level graphs, no row details.
- **`auditor_read_only`**: Read-only access to all fields, no edit/ingest/refresh permissions.

---

## 2. Access Permission Matrix

| Role Key | Allowed Modules | Metric Level | Salary Visibility | ER Case Detail | Talent Rating | Export Permission | Refresh Data | Approval Gate |
|---|---|---|---|---|---|---|---|---|
| `admin_system` | All (`*`) | Row-Level | Yes | Yes | Yes | Yes | Yes | Yes |
| `hr_executive` | All (`*`) | Row-Level | Yes | Yes | Yes | Yes | Yes | Yes |
| `hr_operations_manager` | Exec, DQ, WF, Attendance, Compliance | Row-Level | No | No | Yes | Yes | Yes | No |
| `payroll_manager` | Exec, Payroll | Row-Level | Yes | No | No | Yes | Yes | Yes |
| `employee_relations_manager` | Exec, ER | Row-Level | No | Yes | No | Yes | Yes | Yes |
| `recruitment_manager` | Exec, Recruitment | Row-Level | No | No | No | Yes | Yes | Yes |
| `talent_manager` | Exec, Talent | Row-Level | No | No | Yes | Yes | Yes | Yes |
| `compliance_manager` | Exec, Compliance | Row-Level | No | No | No | Yes | Yes | Yes |
| `project_manager` | Workforce, Attendance | Project Agg | No | No | No | No | No | No |
| `viewer_executive_aggregate_only` | Executive | System Agg | No | No | No | No | No | No |
| `auditor_read_only` | All (`*`) | Row-Level | Yes | Yes | Yes | No | No | No |

---

## 3. Real Data Ingestion Restrictions
Row-level access to live employee identities, GOSI profiles, and compensation metrics is restricted strictly to roles that have signed the [REAL_DATA_ACCESS_SIGNOFF_PACKAGE.md](file:///c:/tmp/HR-DASHBOARD/docs/REAL_DATA_ACCESS_SIGNOFF_PACKAGE.md). General roles view masked or aggregate-only dashboard fields.
