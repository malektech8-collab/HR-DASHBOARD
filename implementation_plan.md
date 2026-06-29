# Implementation Plan — HR Analytics Command Center (Milestone 1)

This plan details the implementation of a local-first HR Analytics Command Center. The system will ingest raw CSV data, run validation checks, process it using Polars and DuckDB, expose it via a FastAPI backend, and visualize it on a React frontend dashboard.

## User Review Required

> [!IMPORTANT]
> **Calculations in Metrics Layer:** All official calculations (e.g., Turnover Rate, Payroll Cost, Overtime Cost, Net Late Minutes) are computed in the database (DuckDB/SQL) or backend service layer. The React frontend will purely display these values.
> **Tailwind & ECharts UI styling:** We will implement a modern dark/neutral slate theme with clean typography and custom layout components matching the mockup requirements.

## Open Questions

- *Do you have a preference for using Vite's React-TS template with simple Tailwind CSS, or do you want a full shadcn/ui installation which might require additional CLI tool configurations?* (We propose standard React + Vite + Tailwind CSS for maximum speed and robustness in local setups).

---

## Proposed Changes

### Repository Structure & Base Config

We will initialize the repository structure specified in the kickoff document.

#### [NEW] [README.md](file:///c:/tmp/HR-DASHBOARD/README.md)
Document local setup, commands to run, and the architecture of the system.

#### [NEW] [PROJECT_BRIEF.md](file:///c:/tmp/HR-DASHBOARD/PROJECT_BRIEF.md)
Contains the vision, scope of Milestone 1, and out-of-scope items.

#### [NEW] [.gitignore](file:///c:/tmp/HR-DASHBOARD/.gitignore)
Ignore the database file (`warehouse/*.duckdb`), local raw data (`data/raw/*`, etc.), node modules, python virtual environments, and `.env`.

#### [NEW] [.env.example](file:///c:/tmp/HR-DASHBOARD/.env.example)
Example environment variables (e.g., `PORT=8000`, `DATABASE_PATH=warehouse/hr_analytics.duckdb`).

---

### Data Engineering & Scripts

#### [NEW] [generate_sample_data.py](file:///c:/tmp/HR-DASHBOARD/scripts/generate_sample_data.py)
Generates representative CSVs in `data/sample/`:
- `employees_sample.csv`
- `payroll_sample.csv`
- `attendance_sample.csv`
- `hr_requests_sample.csv`
- `compliance_sample.csv`
Includes intentional quality issues (e.g., missing managers, duplicates, mismatch salaries) to test the Data Quality page.

#### [NEW] [ingest_raw.py](file:///c:/tmp/HR-DASHBOARD/scripts/ingest_raw.py)
Reads sample CSVs, enforces types, and writes clean Parquet files to `data/bronze/` and `data/silver/`.

#### [NEW] [validate_data.py](file:///c:/tmp/HR-DASHBOARD/scripts/validate_data.py)
Performs validation checks (e.g., checking that employee IDs are unique, net late minutes calculations are correct, gross/net pay are non-negative) and writes a `data_quality_report.parquet` to `data/gold/`.

#### [NEW] [build_warehouse.py](file:///c:/tmp/HR-DASHBOARD/scripts/build_warehouse.py)
Creates/updates `warehouse/hr_analytics.duckdb`. Reads Parquet files and loads them into tables. Creates analytical views:
- `mart_executive_summary`
- `mart_data_quality`

#### [NEW] [refresh_all.py](file:///c:/tmp/HR-DASHBOARD/scripts/refresh_all.py)
Runs the scripts in order: `generate_sample_data.py` -> `ingest_raw.py` -> `validate_data.py` -> `build_warehouse.py`.

---

### Backend (FastAPI)

#### [NEW] [requirements.txt](file:///c:/tmp/HR-DASHBOARD/backend/requirements.txt)
Define backend requirements: `fastapi`, `uvicorn`, `duckdb`, `polars`, `pydantic`, etc.

#### [NEW] [main.py](file:///c:/tmp/HR-DASHBOARD/backend/app/main.py)
FastAPI entry point with middleware, CORS configuration, and router declarations.

#### [NEW] [config.py](file:///c:/tmp/HR-DASHBOARD/backend/app/config.py)
Pydantic config for environment variables.

#### [NEW] [duckdb_client.py](file:///c:/tmp/HR-DASHBOARD/backend/app/db/duckdb_client.py)
Connection pooling / context manager for DuckDB querying.

#### [NEW] [kpi.py](file:///c:/tmp/HR-DASHBOARD/backend/app/schemas/kpi.py)
Pydantic models for the executive summary, metrics, and data quality responses.

#### [NEW] [executive.py](file:///c:/tmp/HR-DASHBOARD/backend/app/api/executive.py)
Router for `/api/executive/summary` retrieving calculations from DuckDB.

#### [NEW] [data_quality.py](file:///c:/tmp/HR-DASHBOARD/backend/app/api/data_quality.py)
Router for `/api/data-quality/summary` and `/api/data-quality/exceptions`.

---

### Frontend (React + Vite + TS)

We will bootstrap the frontend in `frontend/`.

#### [NEW] [package.json](file:///c:/tmp/HR-DASHBOARD/frontend/package.json)
Install standard React, TypeScript, Vite, Tailwind CSS, Lucide icons, Apache ECharts (`echarts`, `echarts-for-react`), and TanStack Table (`@tanstack/react-table`).

#### [NEW] [AppLayout.tsx](file:///c:/tmp/HR-DASHBOARD/frontend/src/components/layout/AppLayout.tsx)
Responsive UI with a Left Sidebar (navigation between pages) and Top Header (showing report month and data refresh status).

#### [NEW] [ExecutiveSummary.tsx](file:///c:/tmp/HR-DASHBOARD/frontend/src/pages/ExecutiveSummary.tsx)
Displays KPI cards (Active Headcount, Joiners, Leavers, Turnover Rate, Payroll Cost, Overtime Cost, Absence Days, Data Quality Score) and two interactive ECharts (Workforce headcount trend & Payroll cost trend).

#### [NEW] [DataQuality.tsx](file:///c:/tmp/HR-DASHBOARD/frontend/src/pages/DataQuality.tsx)
Displays Data Quality Score, missing fields statistics, and an exception table with sorting and pagination.

---

## Verification Plan

### Automated Tests
- Validate python script outputs by running `python scripts/refresh_all.py` and checking if parquet files and `hr_analytics.duckdb` are generated successfully.
- Verify FastAPI backend is running by executing:
  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8000/api/executive/summary
  ```

### Manual Verification
- Start FastAPI backend and React frontend.
- Open `http://localhost:5173/` in a web browser.
- Verify KPI card values are populated from backend.
- Verify Headcount and Payroll trend charts render properly.
- Verify Exception Table on the Data Quality page works with pagination and sorting.
