# Development Log

## [2026-06-25] Initial Implementation (Milestone 1)

### Work Done:
- Setup directory structure and base configuration files.
- Wrote data validation contracts for all CSV files in `data/contracts/`.
- Configured metrics metadata dictionary in `config/metrics_dictionary.yml`.
- Implemented Python fake sample data generator, data ingestion script (using Polars to parquet), data validation script, and warehouse build script (DuckDB client, tables, analytical views).
- Programmed a fastapi backend server with metadata refresh, health, executive summary, and data quality endpoints.
- Bootstrapped a React, Vite, TS, Tailwind CSS app frontend shell.
- Created layout components, dynamic KPI cards, Apache ECharts trends, and a paginated data quality exceptions list using TanStack Table.

## [2026-06-25] Milestone 1 QA Freeze & Approval

- Verified that all frontend KPI cards load values dynamically from backend API responses.
- Verified that official analytics metrics calculations are performed in the backend DuckDB views.
- Verified that git ignore parameters successfully exclude node modules, virtual environments, raw databases, and local Parquet folders.
- Playwright screenshot tests run successfully, saving browser images of the Executive Summary and Data Quality tabs to `docs/qa/screenshots/`.
- Milestone 1 formally accepted.

## [2026-06-25] Milestone 2A Workforce Dashboard Implementation

### Work Done:
- Developed and refined six DuckDB analytical mart views in `scripts/build_warehouse.py`:
  - `mart_workforce_kpis`: Core KPIs such as Active Headcount, Saudi/Non-Saudi splits, Saudization Rate, Probations (90 days since joining), Expiring permits (within 30 days), and missing profile fields.
  - `mart_workforce_headcount_trend`: Historical 3-month headcount trends.
  - `mart_workforce_distribution`: Counts grouped by department, project, nationality group, status, and employment type.
  - `mart_workforce_contract_expiry`: Fixed buckets: `expired`, `"0_30"`, `"31_60"`, `"61_90"`, `"90_plus"`, `missing_date`.
  - `mart_workforce_iqama_expiry`: Fixed buckets matching the contract expiry format (resolves from `compliance` joined by `employee_id`).
  - `mart_workforce_exceptions`: Consolidated audit list of contract expiries, missing properties, and invalid data combinations.
- Implemented six backend REST API routes under `/api/workforce/` (`/summary`, `/trends`, `/distribution`, `/contract-expiry`, `/iqama-expiry`, `/exceptions`).
- Configured Pydantic response models using Field aliases (e.g. `Field(..., alias="0_30")`) to allow keys starting with numbers in serializations.
- Connected the frontend types (`ExpiryAgingData`), API fetch module (`api.ts`), and sidebar navigation shell.
- Built the Workforce Dashboard page (`Workforce.tsx`) using the strict 6-row layout.
- Rebuilt frontend with Tailwind v4 postcss module and verified compiling.
- Captured verified tall browser screenshot to `docs/qa/screenshots/milestone_2a_workforce_dashboard.png`.

## [2026-06-25] Milestone 2A Workforce Data Reconciliation Corrections

### Work Done:
- Created the `base_active_workforce` DuckDB view to serve as the single, deduplicated canonical population of active employees.
- Standardized all active workforce mart views (`mart_workforce_kpis`, `mart_workforce_distribution`, `mart_workforce_contract_expiry`, `mart_workforce_iqama_expiry`, and active checks in `mart_workforce_exceptions`) to query from `base_active_workforce` instead of raw `employees`.
- Substituted all metric-based `COUNT(*)` expressions with `COUNT(DISTINCT employee_id)` to prevent duplication bias.
- Programmed a Python validation assertion block in `scripts/build_warehouse.py` that checks the sums of all distributions and contract expiry buckets against the authoritative `active_headcount` view count, raising a ValueError on mismatch.
- Ran validation tests, confirming perfect database reconciliation (sums equal exactly 19).
- Recaptured verified browser screenshots showing reconciled metrics.

## [2026-06-25] Milestone 2B Payroll & Cost Dashboard Implementation

### Work Done:
- Developed and integrated DuckDB analytical views in `scripts/build_warehouse.py`:
  - `base_payroll_current` and `base_payroll_previous`: Canonical payroll bases left-joining employee records to map department, project, cost center, status, and handle inactive/terminated attributes (defaulting missing fields to descriptive "Missing" values).
  - `mart_payroll_kpis`: Core payroll summary KPIs (Total Cost, Basic salary, Allowances, Overtime, Deductions, Net payroll, Average Cost, Variance MoM, Paid Employees, exceptions).
  - `mart_payroll_trend`: Month-over-month trend of payroll components and paid employee headcount.
  - `mart_payroll_by_project` and `mart_payroll_by_department`: Cost distributions.
  - `mart_payroll_components`: Component aggregate values.
  - `mart_payroll_variance_components` and `mart_payroll_variance_employees`: MoM component and employee variances.
  - `mart_payroll_exceptions`: Reconciled database checks (Gross component mismatch, net payroll mismatch, inactive employee payroll, negative pay checks, missing attributes).
- Added 7 backend API endpoints (`/api/payroll/summary`, `/trends`, `/by-project`, `/by-department`, `/components`, `/variance`, `/exceptions`) with Pydantic serialization models.
- Configured variance thresholds (Basic MoM change > 10%, Gross change > 2000 SAR) inside `config/metrics_dictionary.yml`.
- Programmed a Python validation block inside `scripts/build_warehouse.py` asserting that total sums, project/department totals, paid count, exceptions count, and math reconciliations pass, raising pipeline-breaking errors on mismatch.
- Enabled the navigation link in `SidebarNavigation.tsx` (changing payroll from a placeholder to a fully active route).
- Developed `frontend/src/pages/Payroll.tsx` showing the 6-row ECharts layout.
- Rebuilt frontend successfully using strict TypeScript compilation.
- Captured verified tall browser screenshot to `docs/qa/screenshots/milestone_2b_payroll_dashboard.png`.

## [2026-06-25] Milestone 2C Attendance, Absence & Overtime Dashboard Implementation

### Work Done:
- Developed and integrated DuckDB base views and marts in `scripts/build_warehouse.py`:
  - `base_employees_deduplicated`: Authoritative master employee table deduplicated by employee ID.
  - `base_attendance_current`: Standardized current month attendance records with calculated late and net late minutes.
  - `base_expected_attendance`: Generated expected workday calendar for active employees, used as the denominator for compliance and absence calculations.
  - `base_attendance_payroll_overtime`: Reconciles attendance overtime hours against paid overtime costs from the payroll ledger.
  - `mart_attendance_kpis`: Core KPIs (Compliance %, Absence Days, Late Minutes, Excused Minutes, Net Late Minutes, Early Leave, Missing Punches, OT Hours, OT Cost, Exceptions).
  - `mart_attendance_trend`: Historical trend of compliance, absence, and overtime.
  - `mart_attendance_by_project` and `mart_attendance_by_department`: Compliance, absence, lateness, and overtime distributions.
  - `mart_attendance_late_arrival`: Detailed late arrival incidents and minutes by employee.
  - `mart_attendance_overtime`: Overtime hours and cost reconciliation status.
  - `mart_attendance_missing_punches`: Count of missing check-in/check-out punches by employee.
  - `mart_attendance_exceptions`: Audit log of flagged exceptions (14 checks including punches, excuse rules, and payroll OT matches).
- Coded 14 required exception checks and 8 automated database-level reconciliation assertions in `scripts/build_warehouse.py`.
- Created schemas in `backend/app/schemas/attendance.py` and router in `backend/app/api/attendance.py`, mounting it in `backend/app/main.py`.
- Developed `frontend/src/pages/Attendance.tsx` showing the 6-row ECharts layout.
- Activated the navigation link in `SidebarNavigation.tsx` (changing version in footer to 2C).
- Rebuilt frontend successfully using strict TypeScript compilation.
- Captured verified tall browser screenshot to `docs/qa/screenshots/milestone_2c_attendance_dashboard.png`.

## [2026-06-28] Milestone 2D Saudization, Compliance & Government Platforms Dashboard Implementation

### Work Done:
- Developed and integrated Saudization, GOSI, WPS, and compliance metrics in DuckDB SQL base views and marts.
- Programmed 11 compliance reconciliation checks and automated assertions.
- Created FastAPI backend schemas and router, mounting it at `/api/compliance/*`.
- Developed `frontend/src/pages/Compliance.tsx` showing the 8-row ECharts layout.
- Activated navigation link in `SidebarNavigation.tsx`.
- Captured verified browser screenshot to `docs/qa/screenshots/milestone_2d_compliance_dashboard.png`.

## [2026-06-28] Milestone 2E Employee Relations, Labor Cases & HR Operations SLA Dashboard Implementation

### Work Done:
- Implemented stable row-level keys `er_case_record_id` and pre-filter source views.
- Created FastAPI backend schemas and router, mounting it at `/api/er/*`.
- Developed `frontend/src/pages/EmployeeRelations.tsx` with 11 KPI cards and Exception log.
- Programmed 15 case exception checks and 11 database-level reconciliation assertions.
- Activated navigation link in `SidebarNavigation.tsx`.
- Captured verified browser screenshot to `docs/qa/screenshots/milestone_2e_er_dashboard.png`.

## [2026-06-28] Milestone 2F Recruitment, Workforce Planning & Hiring Pipeline Dashboard Implementation

### Work Done:
- Implemented pre-filter source-level views (`base_requisition_source_records`, `base_candidate_source_records`, etc.) generating stable row-level keys (`requisition_record_id`, `candidate_record_id`, etc.) to prevent join multiplication.
- Configured dynamic targeting: `effective_target_hire_date = COALESCE(target_hire_date, approval_date + default_sla_days)`.
- Standardized canonical fields (`recruiter_id`, `interviewer_id`, `offer_status`, `hire_date`) and normalized candidate sources.
- Built base views and marts resolving open/closed status mappings, recruitment funnel stages, and workforce plan vs actual headcount fulfillment % comparisons.
- Implemented 20 recruitment exception checks and 13 automated database-level reconciliation assertions.
- Created FastAPI backend schemas in `backend/app/schemas/recruitment.py` and router in `backend/app/api/recruitment.py`.
- Developed React dashboard page `frontend/src/pages/Recruitment.tsx` showing the 8-row ECharts and exceptions table.
- Activated navigation link in `SidebarNavigation.tsx`.
- Rebuilt frontend successfully using strict TypeScript compilation.
- Captured verified raw API outputs JSON to `docs/qa/api_outputs/milestone_2f_recruitment_api_outputs.json` and tall dashboard screenshot to `docs/qa/screenshots/milestone_2f_recruitment_dashboard.png`.
- Generated final QA report to `docs/qa/reports/milestone_2f_recruitment_qa_report.md`.
