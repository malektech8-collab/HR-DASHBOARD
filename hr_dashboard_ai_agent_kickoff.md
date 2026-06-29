# HR Analytics Command Center — AI Coding Agent Kickoff Instructions

**Project Owner:** Malek  
**Project Role for ChatGPT:** Project Manager / Solution Architect / QA Reviewer  
**Target Product:** Local-first HR Analytics Command Center  
**Primary Goal:** Build a clean, modern, professional HR dashboard application that is not dependent on Power BI or traditional BI tools.

---

## 0. Read This First

You are the AI coding agent assigned to start this project. Your job is not to generate a flashy demo. Your job is to create a maintainable, scalable, local-first HR analytics product foundation.

The dashboard must eventually support workforce, payroll, attendance, overtime, Saudization/compliance, HR operations SLA, employee relations, final settlement tracking, and data quality monitoring.

The first version must focus on correctness, maintainability, and trusted HR calculations before visual complexity.

### Critical instruction

Do not build calculations directly inside frontend components.

All official HR metrics must flow through this path:

```text
Raw HR files
  -> ingestion
  -> validation
  -> clean modeled data
  -> metric layer
  -> backend API
  -> frontend visual components
```

If you skip the data model and jump directly from Excel/CSV to charts, you are building the wrong system.

---

## 1. Product Vision

Build a local-first HR analytics command center that gives leadership and HR operations a reliable view of:

1. Workforce size, distribution, movement, and risk.
2. Payroll cost, variance, leakage, and exceptions.
3. Attendance, absence, lateness, overtime, and schedule discipline.
4. Saudization and Saudi labor compliance indicators.
5. HR service requests, SLA performance, and bottlenecks.
6. Employee relations and labor case exposure.
7. Data quality issues that may invalidate reports.

The product should feel like a professional SaaS dashboard, even if it runs locally at first.

---

## 2. Approved Technology Stack

Use the following stack unless the project owner explicitly changes it.

### Data and analytics

| Layer | Technology | Purpose |
|---|---|---|
| Raw files | CSV, XLSX | Initial HR/payroll/attendance exports |
| Columnar storage | Parquet | Efficient local analytical storage |
| Data processing | Python + Polars | Fast ingestion, cleaning, typing, and validation |
| Analytics engine | DuckDB | Local analytical SQL engine |
| Transformation / metrics | dbt | Reusable models, metric logic, tests, documentation |

### Backend

| Layer | Technology | Purpose |
|---|---|---|
| API | FastAPI | Serve metrics and dashboard data |
| Validation | Pydantic | Request/response schemas |
| Local auth, later | FastAPI middleware / JWT | Future role-based access |

### Frontend

| Layer | Technology | Purpose |
|---|---|---|
| App framework | React + TypeScript + Vite | Professional frontend foundation |
| UI system | Tailwind CSS + shadcn/ui | Clean modern design system |
| Charts | Apache ECharts | Interactive dashboard visuals |
| Data tables | TanStack Table | Exception lists, sorting, filtering, drilldowns |

### DevOps and packaging

| Layer | Technology | Purpose |
|---|---|---|
| Version control | Git | Change tracking |
| Local packaging | Docker Compose | Repeatable local deployment |
| Environment config | `.env` files | Local configuration |

---

## 3. Authoritative References

Use official documentation as the first reference when implementing libraries:

- DuckDB documentation: https://duckdb.org/docs/current/
- DuckDB Parquet documentation: https://duckdb.org/docs/current/data/parquet/overview.html
- Polars documentation: https://docs.pola.rs/
- dbt documentation: https://docs.getdbt.com/docs/introduction
- dbt data tests: https://docs.getdbt.com/docs/build/data-tests
- FastAPI documentation: https://fastapi.tiangolo.com/
- React documentation: https://react.dev/
- Vite documentation: https://vite.dev/guide/
- Apache ECharts documentation: https://echarts.apache.org/
- TanStack Table documentation: https://tanstack.com/table/latest/docs/introduction
- shadcn/ui documentation: https://ui.shadcn.com/docs

---

## 4. Non-Negotiable Engineering Rules

### 4.1 Do not create a BI toy

This is not a notebook, not an Excel macro project, and not a one-page demo.

It must be structured like a product.

### 4.2 Keep formulas out of the frontend

Bad:

```typescript
const turnoverRate = leavers / headcount;
```

Good:

```text
dbt model calculates turnover_rate
FastAPI serves turnover_rate
React displays turnover_rate
```

### 4.3 Build from fake/sample data first

Do not require real HR files in the initial commit. Create safe sample datasets with fake employees, fake payroll, fake attendance, and fake compliance records.

### 4.4 HR data is sensitive

Never commit real HR data. Add `/data/raw`, `/data/bronze`, `/data/silver`, `/data/gold`, and `/warehouse` to `.gitignore`, except for explicitly safe sample files.

### 4.5 Every metric must be traceable

Each dashboard metric must eventually answer:

- What source table created it?
- What formula calculated it?
- What filters affect it?
- What data quality issues may invalidate it?

### 4.6 Exception tables are mandatory

Every major dashboard page must include a section called:

```text
Exceptions Requiring Action
```

The dashboard must not only report. It must guide action.

---

## 5. Initial Repository Structure

Create this structure:

```text
hr-analytics-command-center/
│
├── README.md
├── PROJECT_BRIEF.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── executive.py
│   │   │   ├── workforce.py
│   │   │   ├── payroll.py
│   │   │   ├── attendance.py
│   │   │   ├── compliance.py
│   │   │   └── data_quality.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── duckdb_client.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   └── kpi.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── metrics_service.py
│   │       └── health_service.py
│   │
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── formatters.ts
│   │   │   └── types.ts
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── cards/
│   │   │   ├── charts/
│   │   │   ├── tables/
│   │   │   └── filters/
│   │   ├── pages/
│   │   │   ├── ExecutiveSummary.tsx
│   │   │   ├── Workforce.tsx
│   │   │   ├── Payroll.tsx
│   │   │   ├── Attendance.tsx
│   │   │   └── DataQuality.tsx
│   │   └── styles/
│   │       └── globals.css
│   │
│   └── public/
│
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   ├── bronze/
│   │   └── .gitkeep
│   ├── silver/
│   │   └── .gitkeep
│   ├── gold/
│   │   └── .gitkeep
│   └── sample/
│       ├── employees_sample.csv
│       ├── payroll_sample.csv
│       ├── attendance_sample.csv
│       ├── hr_requests_sample.csv
│       └── compliance_sample.csv
│
├── warehouse/
│   └── .gitkeep
│
├── dbt_hr/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_employees.sql
│   │   │   ├── stg_payroll.sql
│   │   │   ├── stg_attendance.sql
│   │   │   ├── stg_hr_requests.sql
│   │   │   └── stg_compliance.sql
│   │   ├── intermediate/
│   │   │   ├── int_employee_monthly_snapshot.sql
│   │   │   ├── int_payroll_variance.sql
│   │   │   └── int_attendance_summary.sql
│   │   └── marts/
│   │       ├── mart_executive_summary.sql
│   │       ├── mart_workforce.sql
│   │       ├── mart_payroll.sql
│   │       ├── mart_attendance.sql
│   │       └── mart_data_quality.sql
│   │
│   └── tests/
│
├── scripts/
│   ├── generate_sample_data.py
│   ├── ingest_raw.py
│   ├── validate_data.py
│   ├── build_warehouse.py
│   └── refresh_all.py
│
└── docs/
    ├── architecture.md
    ├── data_dictionary.md
    ├── metric_definitions.md
    ├── dashboard_pages.md
    └── backlog.md
```

---

## 6. First Milestone Scope

The first milestone is not the full HR dashboard.

The first milestone is:

```text
A working local app with sample data, DuckDB warehouse, FastAPI endpoints, and a clean React executive dashboard shell.
```

### Milestone 1 must include

1. Repository structure.
2. Sample data generator.
3. Data ingestion from sample CSV files.
4. DuckDB database creation.
5. Basic dbt-style SQL models or SQL transformation scripts if dbt setup needs to be deferred.
6. FastAPI health endpoint.
7. FastAPI executive summary endpoint.
8. React dashboard layout with sidebar navigation.
9. Executive Summary page with KPI cards and placeholder charts connected to backend data.
10. Data Quality page with sample exception table.
11. README with local run instructions.

---

## 7. MVP Pages

Only build these five pages first:

1. Executive Summary
2. Workforce
3. Payroll & Cost
4. Attendance & Overtime
5. Data Quality

Do not build recruitment, employee relations, final settlement, or advanced compliance in the first sprint unless instructed later.

---

## 8. Dashboard Design Requirements

### 8.1 Layout

Use a modern SaaS layout:

```text
Left sidebar navigation
Top header with report month and refresh status
Main content area
KPI card row
Charts section
Exception table section
```

### 8.2 Visual tone

The UI must be:

- Clean
- Modern
- Executive-friendly
- Low-noise
- Professional
- Neutral color palette
- High contrast for risk statuses
- Suitable for Arabic/English future localization

### 8.3 Color usage

Use color only to communicate meaning:

| Color Meaning | Usage |
|---|---|
| Healthy | Positive status |
| Warning | Attention required |
| Critical | Immediate risk |
| Neutral | Normal values |

Do not use decorative random colors.

### 8.4 Components required

Create reusable components:

```text
KpiCard
PageHeader
FilterBar
ChartCard
RiskBadge
StatusBadge
ExceptionTable
SidebarNavigation
DateRefreshIndicator
```

---

## 9. Initial Dashboard Metrics

### 9.1 Executive Summary KPIs

Create these initial KPIs from sample data:

| KPI | Definition |
|---|---|
| Active Headcount | Count of employees where status = Active |
| Joiners This Month | Employees with joining date within selected month |
| Leavers This Month | Employees with termination date within selected month |
| Turnover Rate | Leavers this month / average active headcount |
| Payroll Cost | Total gross pay for selected month |
| Overtime Cost | Total overtime amount for selected month |
| Absence Days | Total unapproved absence days |
| Data Quality Score | Valid required fields / total required fields |

### 9.2 Workforce page KPIs

| KPI | Definition |
|---|---|
| Active Headcount | Active employees |
| Saudis | Active Saudi employees |
| Non-Saudis | Active non-Saudi employees |
| Employees by Project | Count by project |
| Employees by Department | Count by department |
| Contract Expiry 30/60/90 | Active contracts expiring soon |

### 9.3 Payroll page KPIs

| KPI | Definition |
|---|---|
| Gross Payroll | Sum of gross pay |
| Basic Salary Cost | Sum of basic salaries |
| Allowance Cost | Sum of allowances |
| Overtime Cost | Sum of overtime amount |
| Deduction Amount | Sum of deductions |
| Payroll Variance | Current month payroll - previous month payroll |

### 9.4 Attendance page KPIs

| KPI | Definition |
|---|---|
| Absence Days | Sum of absence days |
| Late Minutes | Sum of late minutes |
| Excused Late Minutes | Sum of approved excused late minutes |
| Net Late Minutes | Late minutes - excused late minutes |
| Overtime Hours | Sum of approved overtime hours |
| Missing Punches | Count of missing punch incidents |

### 9.5 Data Quality KPIs

| KPI | Definition |
|---|---|
| Missing Manager | Active employees with no manager ID |
| Missing Project | Active employees with no project |
| Missing Cost Center | Active employees with no cost center |
| Missing Nationality | Employees with no nationality |
| Duplicate Employee ID | Duplicate employee numbers |
| Invalid Payroll Record | Paid employee not active or missing payroll period |

---

## 10. Sample Data Requirements

Generate fake data only.

### 10.1 employees_sample.csv

Required columns:

```text
employee_id
employee_name
nationality
is_saudi
company
department
project
job_title
job_family
grade
manager_id
cost_center
employment_type
contract_type
joining_date
termination_date
contract_end_date
status
basic_salary
housing_allowance
transport_allowance
```

### 10.2 payroll_sample.csv

Required columns:

```text
payroll_period
employee_id
basic_salary
housing_allowance
transport_allowance
other_allowances
overtime_amount
deductions
gross_pay
net_pay
project
cost_center
payroll_status
```

### 10.3 attendance_sample.csv

Required columns:

```text
attendance_date
employee_id
shift_name
scheduled_start
scheduled_end
actual_check_in
actual_check_out
late_minutes
excused_late_minutes
net_late_minutes
absence_days
overtime_hours
overtime_approved
missing_punch_count
project
```

### 10.4 hr_requests_sample.csv

Required columns:

```text
request_id
employee_id
request_type
request_status
created_at
closed_at
owner
sla_hours
actual_hours
sla_breached
project
```

### 10.5 compliance_sample.csv

Required columns:

```text
employee_id
period
qiwa_status
gosi_status
mudad_status
contract_authenticated
gosi_salary
payroll_basic_salary
occupation_code
occupation_match_status
work_permit_expiry
iqama_expiry
insurance_status
```

---

## 11. Backend API Requirements

Use FastAPI.

### Required endpoints for Milestone 1

```text
GET /health
GET /api/meta/refresh-status
GET /api/executive/summary
GET /api/workforce/summary
GET /api/payroll/summary
GET /api/attendance/summary
GET /api/data-quality/summary
GET /api/data-quality/exceptions
```

### Response style

Return clean JSON with predictable schema.

Example:

```json
{
  "report_month": "2026-06",
  "last_refresh_at": "2026-06-25T10:00:00+03:00",
  "kpis": [
    {
      "key": "active_headcount",
      "label": "Active Headcount",
      "value": 2107,
      "unit": "employees",
      "trend_value": 2.4,
      "trend_direction": "up",
      "status": "healthy"
    }
  ],
  "charts": {
    "headcount_trend": [],
    "payroll_trend": []
  },
  "exceptions": []
}
```

### Filtering

Prepare API functions to accept optional filters later:

```text
month
company
project
department
nationality
employment_type
```

Do not overbuild filters in Milestone 1, but structure code so filters can be added easily.

---

## 12. Frontend Requirements

### 12.1 Pages

Create the following routes:

```text
/
/workforce
/payroll
/attendance
/data-quality
```

### 12.2 Layout

Use reusable layout components:

```text
AppLayout
SidebarNavigation
TopBar
PageHeader
ContentGrid
```

### 12.3 KPI cards

Each KPI card should show:

```text
Label
Value
Unit
Trend
Status
Small description
```

### 12.4 Charts

Use Apache ECharts wrappers.

Create reusable chart components:

```text
LineChartCard
BarChartCard
HeatmapChartCard
DonutChartCard
GaugeChartCard
```

In Milestone 1, it is acceptable to implement only:

```text
LineChartCard
BarChartCard
```

### 12.5 Exception tables

Use TanStack Table for exceptions.

Minimum table capabilities:

```text
Sorting
Filtering
Pagination
Status badge column
Action required column
```

---

## 13. Data Processing Requirements

### 13.1 Ingestion

Create `scripts/ingest_raw.py` to:

1. Read sample CSV files from `/data/sample`.
2. Normalize column names.
3. Enforce expected schemas.
4. Cast dates and numeric fields.
5. Write cleaned Parquet files to `/data/bronze` or `/data/silver`.

### 13.2 Validation

Create `scripts/validate_data.py` to check:

| Check | Rule |
|---|---|
| Employee ID | Not null |
| Employee ID | Unique in employee master |
| Payroll employee ID | Must exist in employee master |
| Attendance employee ID | Must exist in employee master |
| Status | Must be Active, Inactive, Terminated, On Leave |
| Gross pay | Must be >= 0 |
| Net pay | Must be >= 0 |
| Late minutes | Must be >= 0 |
| Net late minutes | Must equal late minutes - excused late minutes |
| Joining date | Must not be null |

Validation should create a report:

```text
/data/gold/data_quality_report.parquet
```

### 13.3 Warehouse build

Create `scripts/build_warehouse.py` to:

1. Create or update `/warehouse/hr_analytics.duckdb`.
2. Load Parquet data into DuckDB views or tables.
3. Create core mart tables/views.
4. Prepare data for FastAPI queries.

### 13.4 Full refresh

Create `scripts/refresh_all.py` to run:

```text
generate_sample_data.py
ingest_raw.py
validate_data.py
build_warehouse.py
```

---

## 14. Data Model Requirements

### 14.1 Core dimensions

Prepare for these dimensions:

```text
dim_employee
dim_date
dim_company
dim_department
dim_project
dim_job
dim_manager
dim_cost_center
```

### 14.2 Core facts

Prepare for these fact tables:

```text
fact_headcount_snapshot
fact_payroll
fact_attendance
fact_overtime
fact_hr_requests
fact_compliance
fact_data_quality_issues
```

### 14.3 Employee monthly snapshot

This is mandatory.

Create or prepare logic for:

```text
fact_headcount_snapshot
```

Minimum fields:

```text
snapshot_month
employee_id
status
company
department
project
job_title
job_family
grade
manager_id
cost_center
nationality
is_saudi
basic_salary
contract_type
contract_end_date
```

Reason:

HR reporting must preserve historical context. If an employee moves projects, historical headcount and payroll must not be overwritten by the latest project only.

---

## 15. Metric Definitions for Milestone 1

Implement these metric definitions in SQL or metric service layer, preferably SQL/dbt.

### 15.1 Active headcount

```sql
COUNT(DISTINCT employee_id)
WHERE status = 'Active'
```

### 15.2 Joiners this month

```sql
COUNT(DISTINCT employee_id)
WHERE joining_date BETWEEN month_start AND month_end
```

### 15.3 Leavers this month

```sql
COUNT(DISTINCT employee_id)
WHERE termination_date BETWEEN month_start AND month_end
```

### 15.4 Turnover rate

```sql
leavers_this_month / average_active_headcount
```

If average active headcount is unavailable in Milestone 1, use:

```sql
leavers_this_month / active_headcount
```

But mark the definition clearly as temporary.

### 15.5 Payroll cost

```sql
SUM(gross_pay)
WHERE payroll_period = selected_month
```

### 15.6 Overtime cost

```sql
SUM(overtime_amount)
WHERE payroll_period = selected_month
```

### 15.7 Net late minutes

```sql
SUM(late_minutes - excused_late_minutes)
```

Never allow net late minutes to go below zero at the row level:

```sql
GREATEST(late_minutes - excused_late_minutes, 0)
```

### 15.8 Data quality score

```text
valid_required_field_checks / total_required_field_checks
```

---

## 16. Coding Standards

### 16.1 Python

- Use clear modules.
- Use type hints where practical.
- Avoid large monolithic scripts.
- Use constants for file paths.
- Use Pydantic for API schemas.
- Add docstrings for business-critical functions.

### 16.2 SQL

- Use readable CTEs.
- Avoid hidden magic numbers.
- Comment business logic.
- Keep one model purpose per SQL file.

### 16.3 TypeScript / React

- Use typed API responses.
- Keep visual components reusable.
- Do not duplicate formatting logic.
- Keep page components clean.
- Do not calculate official HR metrics in React.

### 16.4 Naming

Use English technical naming in code.

Good:

```text
active_headcount
payroll_period
net_late_minutes
sla_breached
```

Avoid:

```text
x1
final2
new_table
calc_data
```

---

## 17. UI/UX Requirements

### 17.1 Executive Summary Page

The page must contain:

1. Page title: `Executive Summary`
2. Last refresh indicator
3. Selected month indicator
4. KPI card row
5. Workforce trend chart
6. Payroll trend chart
7. Risk / exceptions panel
8. Data quality warning if score is below threshold

### 17.2 Data Quality Page

This page must be treated as a first-class page, not an afterthought.

Include:

1. Data Quality Score
2. Missing Manager count
3. Missing Project count
4. Missing Cost Center count
5. Duplicate Employee ID count
6. Exception table
7. Severity badge
8. Recommended action column

---

## 18. Security and Privacy Rules

1. Do not commit real employee data.
2. Do not hardcode personal data.
3. Do not include real salary information in sample data.
4. Do not send HR data to external APIs.
5. Keep AI-generated summaries limited to aggregated data unless explicitly approved.
6. Add `.gitignore` rules for local data and warehouse files.
7. Add `.env.example`, but never commit `.env`.

Required `.gitignore` entries:

```gitignore
data/raw/*
data/bronze/*
data/silver/*
data/gold/*
warehouse/*.duckdb
warehouse/*.wal
.env
__pycache__/
node_modules/
dist/
.venv/
```

Keep `.gitkeep` files where needed.

---

## 19. Documentation Requirements

Create these docs early:

### 19.1 `PROJECT_BRIEF.md`

Include:

- Product objective
- Target users
- First milestone scope
- Out-of-scope items
- Stack
- Run instructions

### 19.2 `docs/architecture.md`

Include:

- Data flow diagram
- Component responsibilities
- Local-first design explanation
- Future upgrade path

### 19.3 `docs/data_dictionary.md`

Include:

- Table names
- Column names
- Data types
- Business meaning

### 19.4 `docs/metric_definitions.md`

Include:

- KPI name
- Formula
- Source table
- Filters
- Known limitations

### 19.5 `docs/backlog.md`

Include:

- Milestone 1 tasks
- Milestone 2 tasks
- Future ideas
- Known risks

---

## 20. Milestone 1 Task Breakdown

Complete the work in this order.

### Task 1 — Initialize repository

Create repository structure, gitignore, README, env example, and basic documentation.

Acceptance criteria:

- Project folder structure exists.
- README explains local setup.
- Sensitive data folders are ignored.

### Task 2 — Generate sample data

Create `scripts/generate_sample_data.py`.

Acceptance criteria:

- Generates all required sample CSV files.
- Uses fake but realistic HR data.
- Includes multiple projects, departments, nationalities, statuses, and payroll periods.

### Task 3 — Ingest and clean data

Create `scripts/ingest_raw.py`.

Acceptance criteria:

- Reads sample CSV files.
- Applies schema checks.
- Writes cleaned Parquet outputs.

### Task 4 — Validate data

Create `scripts/validate_data.py`.

Acceptance criteria:

- Produces data quality issues.
- Identifies missing required fields.
- Identifies duplicate employee IDs.
- Identifies payroll records for unknown employees.

### Task 5 — Build DuckDB warehouse

Create `scripts/build_warehouse.py`.

Acceptance criteria:

- Creates `warehouse/hr_analytics.duckdb` locally.
- Creates tables or views for employees, payroll, attendance, compliance, HR requests, and data quality.
- Creates initial mart views for executive summary and data quality.

### Task 6 — Build FastAPI backend

Create FastAPI app.

Acceptance criteria:

- `/health` returns status OK.
- `/api/executive/summary` returns real values from DuckDB.
- `/api/data-quality/summary` returns real values from DuckDB.

### Task 7 — Build React frontend shell

Create frontend using React + TypeScript + Vite.

Acceptance criteria:

- App runs locally.
- Sidebar exists.
- Top bar exists.
- Executive Summary page exists.
- Data Quality page exists.

### Task 8 — Connect frontend to backend

Acceptance criteria:

- KPI cards load from FastAPI.
- Loading and error states exist.
- No hardcoded KPI values remain except fallback/demo states.

### Task 9 — Add charts and tables

Acceptance criteria:

- Executive Summary includes at least one line chart and one bar chart.
- Data Quality includes an exception table.
- Table supports sorting and pagination.

### Task 10 — Add refresh script

Create `scripts/refresh_all.py`.

Acceptance criteria:

- One command regenerates sample data, ingests, validates, and rebuilds warehouse.

---

## 21. First Sprint Deliverable

The first sprint is complete only when the following command sequence works:

```bash
python scripts/refresh_all.py
cd backend
uvicorn app.main:app --reload
cd ../frontend
npm install
npm run dev
```

And the browser shows:

1. Executive Summary page.
2. KPI cards populated from backend.
3. At least two charts populated from backend.
4. Data Quality page with exception table.
5. No real HR data included.

---

## 22. Definition of Done

A task is not done until:

1. It runs locally.
2. It is documented.
3. It uses sample data only.
4. It avoids hardcoded business metrics in the frontend.
5. It follows the approved folder structure.
6. It does not expose sensitive HR data.
7. It includes basic error handling.
8. It can be reviewed by the project manager.

---

## 23. Project Manager Review Protocol

After each major task, report back with:

```text
Task completed:
Files created/changed:
How to run/test:
Known limitations:
Questions/blockers:
```

Do not move to a larger scope before the project manager reviews the current milestone.

---

## 24. Common Mistakes to Avoid

Avoid these mistakes:

1. Building charts before the data model.
2. Putting formulas in React.
3. Creating too many pages too early.
4. Using real employee data in the repo.
5. Ignoring data quality.
6. Treating data quality as a technical issue only.
7. Mixing raw and cleaned data.
8. Hardcoding project names or employee names.
9. Overbuilding authentication in Milestone 1.
10. Using AI-generated assumptions as official HR formulas.

---

## 25. Future Roadmap

### Milestone 2

- Add Workforce page fully.
- Add Payroll page fully.
- Add Attendance page fully.
- Add month/project/department filters.
- Add trend comparisons.
- Add export to CSV for exception tables.

### Milestone 3

- Add Saudization and Compliance page.
- Add Qiwa/GOSI/Mudad style reconciliation tables.
- Add contract expiry and work permit expiry alerts.

### Milestone 4

- Add HR Operations SLA page.
- Add request aging.
- Add owner workload.
- Add bottleneck analysis.

### Milestone 5

- Add Employee Relations and Labor Cases page.
- Add case severity.
- Add aging and exposure.

### Milestone 6

- Add AI insight summaries over aggregated data only.
- Add executive narrative generator.
- Add anomaly explanation.

### Milestone 7

- Add optional authentication.
- Add role-based views.
- Add deployment to internal server.

---

## 26. Initial Command Prompt for the AI Coding Agent

Use this as the first instruction to start implementation:

```text
You are building a local-first HR Analytics Command Center. Create the initial repository foundation using Python, Polars, DuckDB, Parquet, FastAPI, React, TypeScript, Vite, Tailwind CSS, Apache ECharts, and TanStack Table.

Do not create a simple demo. Create a maintainable product foundation.

Start with Milestone 1 only:
1. Create the repository structure.
2. Add README, PROJECT_BRIEF, .gitignore, .env.example, and docs.
3. Create fake HR sample data generator.
4. Create ingestion, validation, and DuckDB warehouse scripts.
5. Create FastAPI backend with /health and executive summary endpoints.
6. Create React frontend shell with sidebar, topbar, Executive Summary page, and Data Quality page.
7. Connect frontend KPI cards to backend data.
8. Keep official calculations out of React.
9. Do not use real HR data.
10. Stop after Milestone 1 and report files changed, how to run, and known limitations.
```

---

## 27. Final Reminder

The objective is not to impress with visuals first.

The objective is to build trusted HR analytics infrastructure that can later become a polished dashboard product.

The correct sequence is:

```text
Trustworthy data -> reliable metrics -> clean APIs -> professional visuals -> AI insights
```

Do not reverse this order.
