# PROJECT BRIEF: HR Analytics Command Center

## Product Objective
Build a local-first HR analytics command center that gives leadership and HR operations a single, trustworthy, and audit-ready view of workforce headcount, payroll costs, attendance patterns, compliance indicators, and data quality exceptions. The app runs entirely locally using modern open-source data tools.

## Target Users
- **HR Directors & Officers**: To monitor payroll leakage, compliance, and headcount trends.
- **HR Operations Managers**: To track and fix data quality issues in employee master logs.
- **C-Suite/Executive Team**: To see high-level trends and KPIs regarding organizational costs.

## First Milestone Scope (Milestone 1)
- Repository directory structure and configuration.
- Fake HR sample data generator containing intentional quality issues.
- Ingestion pipeline using Polars, writing Parquet.
- Validation checks creating a detailed data quality report.
- Analytical database built using DuckDB, exposing executive KPI and data quality views.
- FastAPI backend serving structured JSON.
- React frontend shell with layout sidebar, Executive Summary (with KPI cards and Apache ECharts trends), and Data Quality page (with TanStack Table for exceptions).

## Out-of-Scope (Milestone 1)
- Advanced filter controls (month/project/department) inside components (modeled for future).
- Real employee data.
- Production authentication or roles.
- Docker compose packaging and production server deployment.
- Milestone 2+ pages (Workforce, Payroll, Attendance dashboards are placeholder links in the sidebar).

## Technology Stack
- **Data & Ingestion**: Python 3.11, Polars, Parquet
- **Analytics Engine**: DuckDB
- **Backend**: FastAPI, Pydantic, Uvicorn
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Apache ECharts, TanStack Table

## Run Instructions
Refer to [README.md](file:///c:/tmp/HR-DASHBOARD/README.md) for full commands.
