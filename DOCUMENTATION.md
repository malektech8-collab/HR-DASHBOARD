# HR Analytics Command Center — Comprehensive Documentation

> **v1.0.0 "Genesis"** — first production release · tagged 2026-07-08 · frozen at this commit on the `production` branch

## 1. Purpose

The HR Analytics Command Center is a **local-first HR analytics dashboard** that gives HR leadership, HR operations, and executives a single, trustworthy, audit-ready view of workforce headcount, payroll cost, attendance, compliance, recruitment, talent, and employee-relations data — plus a data-quality layer that surfaces bad/missing records instead of hiding them.

It doubles as a **synthetic governance-process simulation**: a large body of docs/config (`docs/`, `config/`) model a fictitious multi-gate approval workflow ("Gate 1"–"Gate 5") for eventually loading real company data, complete with sign-offs, risk registers, and a role-gated `/api/governance/status` API. **No real employee data is ever used** — this is explicitly and permanently out of scope (see [Governance & Synthetic-Data Rules](#12-governance--synthetic-data-rules)).

### Target Users
- **HR Directors/Officers** — payroll leakage, compliance, headcount trends
- **HR Operations** — data-quality exceptions, record remediation
- **Executives** — high-level KPIs and cross-domain trends

## 2. Project Stage & Version

| | |
|---|---|
| **Release name** | **v1.0.0 "Genesis"** — first production version |
| **Previous tag** | `v0.1.1-synthetic-governance-rc` (2026-06-30, release-candidate stage) |
| **This release** | `v1.0.0` tag + `production` branch, both pinned to this commit |
| **Maturity** | Working local MVP+ across 9 analytical domains, containerized, with auth, testing, and CI |
| **Deployment target** | Local only (Docker Compose or dev servers). No cloud/production deployment exists. |

Major work landed since the previous tag (chronological), all folded into this release: JWT-based RBAC, TanStack Query state management, DuckDB concurrency hardening (read-only connections via FastAPI `Depends`), Vitest/RTL unit testing, Playwright E2E testing, Tailwind component standardization, Recharts migration (replacing Apache ECharts), route-level code splitting, table virtualization, dbt-duckdb integration (raw SQL moved out of FastAPI into dbt models), S3/cloud-storage abstraction via DuckDB `httpfs`, Docker containerization, GitHub Actions CI/CD, a local "Power BI-style" workspace profile, data-template download/upload fixes, and a light/dark theming system with a company-logo branding feature.

See [§17](#17-versioning--release-policy) for how this release is protected from future changes.

The pre-existing top-level docs (`README.md`, `PROJECT_BRIEF.md`, `docs/ARCHITECTURE.md`) predate most of this and describe an earlier Milestone-1 state (e.g. they still reference Apache ECharts and list Docker/RBAC as "out of scope"). This document supersedes them as the current source of truth; see [§16](#16-relationship-to-existing-docs) for how they relate.

## 3. Feature Overview

### Analytical domains (one page + one API namespace each)
| Domain | Page | Covers |
|---|---|---|
| Command Center | `CommandCenter.tsx` | System/module health, priority alerts, data freshness, QA index — the landing page |
| Executive Summary | `ExecutiveSummary.tsx` | Cross-domain KPIs (headcount, payroll, turnover, OT cost, absence, data-quality score) and trends |
| Workforce | `Workforce.tsx` | Headcount by dept/project, contract & Iqama expiry aging, trends |
| Payroll | `Payroll.tsx` | Cost summary/trends, by-project/department, salary components, variance analysis |
| Attendance | `Attendance.tsx` | Daily metrics, trends, late arrivals, overtime, missing punches |
| Compliance | `Compliance.tsx` | Saudization %, document-expiry aging, GOSI/WPS status |
| Employee Relations | `EmployeeRelations.tsx` | Case trends, types, status, SLA performance, aging |
| Recruitment | `Recruitment.tsx` | Pipeline, time-to-fill, source effectiveness, offer acceptance, onboarding, plan vs actual |
| Talent | `Talent.tsx` | Performance distribution, goals, competency gaps, learning, succession, flight risk |
| Data Quality | `DataQuality.tsx` | Overall DQ score, exception list, templates for corrected data upload |

Every domain also exposes an `.../exceptions` endpoint — records that failed validation are never silently dropped; they surface as actionable exceptions in the UI.

### Cross-cutting features
- **Light/Dark/System theming** — `ThemeContext`, persisted to `localStorage`, driven by a semantic color-token system (`--card`, `--healthy`, `--warning`, `--critical`, `--muted`, etc.) defined in `frontend/src/styles/globals.css` and mapped in `tailwind.config.js`.
- **Company branding** — `BrandingContext` lets a user upload a logo (validated, ≤1MB, stored as a data URL in `localStorage`) shown in the sidebar/header via the Appearance menu.
- **JWT-based RBAC** — three synthetic roles gate the governance status API (see [§9](#9-authentication--rbac)).
- **Data upload/refresh** — CSV template download, upload → Parquet conversion, and a one-click pipeline refresh from the Data Quality page.
- **Responsive layout** — mobile sidebar drawer, responsive charts/tables, virtualized table rendering for large exception lists.
- **Data-quality-first design** — official calculations live only in DuckDB/dbt views, never recomputed in the frontend, so every screen agrees with every other screen.

## 4. Architecture

```
Raw CSVs (data/sample or data/raw)
        │  scripts/ingest_raw.py (Polars)
        ▼
Bronze/Silver Parquet (data/bronze, data/silver)
        │  dbt-duckdb models (dbt_analytics/models/staging, marts)
        ▼
DuckDB Warehouse (warehouse/hr_analytics.duckdb)
        │  FastAPI (read-only Depends-injected connections)
        ▼
REST JSON API (backend/app/api/*)
        │  TanStack Query
        ▼
React SPA (frontend/src, Vite + TypeScript + Tailwind + Recharts)
```

Strict rule carried through the whole stack: **no analytical math in the frontend** — every KPI, trend, and aggregation is computed in a dbt/DuckDB view (`base_*`, `stg_*`, `mart_*`) and served as-is.

## 5. Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Python 3.11, Polars |
| Transformation | dbt-core 1.8.2 + dbt-duckdb 1.8.1 (views: `stg_*`, `base_*`, `mart_*`) |
| Warehouse | DuckDB 1.0.0 (file-based, read-only query connections, optional S3/`httpfs` access) |
| Backend API | FastAPI 0.111, Pydantic 2.7, Uvicorn, PyJWT (RBAC) |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4 |
| Data/state | TanStack Query 5, TanStack Table 8 |
| Charts | Recharts 2.15 (replaced Apache ECharts) |
| Icons | lucide-react |
| Testing | Vitest 4 + React Testing Library (unit), Playwright 1.61 (E2E), Pytest (backend) |
| Lint | oxlint (frontend), flake8 (backend) |
| Containerization | Docker Compose (backend: python:3.11-slim; frontend: Node 22 Alpine build → Nginx Alpine serve) |
| CI/CD | GitHub Actions (`.github/workflows/ci-cd-pipeline.yml`) — lint/typecheck → tests → Docker build verification |

## 6. Repository Structure

```
HR-DASHBOARD/
├── backend/            FastAPI app, API routes, auth, DuckDB client, pytest tests
├── frontend/            React SPA (pages, components, context, hooks, e2e tests)
├── dbt_analytics/        dbt project — 157 SQL models (23 staging + 134 marts)
├── scripts/              Data pipeline orchestration scripts (ingest, build, validate, refresh)
├── config/               ~66 YAML files: business rules, metrics dictionary, governance-gate config
├── data/                 sample/raw/bronze/silver/gold data lake (gitignored beyond samples)
├── warehouse/            DuckDB database file (gitignored)
├── docs/                 Architecture notes + ~100 synthetic-governance process documents
├── docker-compose.yml    Local backend+frontend container orchestration
├── README.md / PROJECT_BRIEF.md / AGENTS.md   Legacy Milestone-1 docs + governance rules
└── DOCUMENTATION.md      This file
```

## 7. Backend API Reference

Base URL (dev): `http://127.0.0.1:8000` · Base URL (Docker): `http://localhost:8080` (proxied) or `:8000` direct.

| Namespace | File | Key endpoints |
|---|---|---|
| Root | `app/main.py` | `GET /health`, `GET /api/meta/refresh-status` |
| Executive | `api/executive.py` | `GET /api/executive/summary` |
| Command Center | `api/command_center.py` | `overview`, `module-health`, `priority-alerts`, `exceptions`, `data-freshness`, `filter-options`, `navigation-status`, `qa-index` |
| Workforce | `api/workforce.py` | `summary`, `trends`, `distribution`, `contract-expiry`, `iqama-expiry`, `exceptions` |
| Payroll | `api/payroll.py` | `summary`, `trends`, `by-project`, `by-department`, `components`, `variance`, `exceptions` |
| Attendance | `api/attendance.py` | `summary`, `trends`, `by-project`, `by-department`, `late-arrival`, `overtime`, `missing-punches`, `exceptions` |
| Compliance | `api/compliance.py` | `summary`, `saudization`, `saudization-by-project`, `saudization-by-department`, `document-expiry`, `gosi`, `wps`, `exceptions` |
| Employee Relations | `api/er.py` | `summary`, `trends`, `by-project`, `by-department`, `case-types`, `status`, `sla`, `aging`, `exceptions` |
| Recruitment | `api/recruitment.py` | `summary`, `pipeline`, `trends`, `by-project`, `by-department`, `time-to-fill`, `source-effectiveness`, `offers`, `onboarding`, `workforce-plan`, `exceptions` |
| Talent | `api/talent.py` | `summary`, `performance-distribution`, `trends`, `by-project`, `by-department`, `goals`, `competency-gaps`, `learning`, `learning-by-project`, `succession`, `succession-readiness`, `risk`, `exceptions` |
| Data Quality | `api/data_quality.py` | `summary`, `exceptions` |
| Data Management | `api/data.py` | `GET templates`, `POST upload` (CSV→Parquet), `POST refresh` (re-run pipeline) |
| Governance | `api/endpoints/governance.py` | `POST /api/governance/token` (login), `GET /api/governance/status` (role-gated) |

All routes are `GET` except the data-management upload/refresh and governance-token endpoints, which are `POST`.

## 8. Frontend Structure

- **Entry**: `frontend/src/main.tsx` — wraps the app in `ThemeProvider` → `BrandingProvider` → `QueryClientProvider`.
- **Routing**: no React Router — `App.tsx` uses a `currentPage` state + switch statement. 9 of 10 pages are `React.lazy()`-loaded with a `PageSkeleton` `Suspense` fallback; `CommandCenter` (the landing page) is statically imported for instant first paint.
- **Data fetching**: `frontend/src/lib/api.ts` (50+ typed fetch functions) + `frontend/src/lib/queryClient.ts` (TanStack Query defaults: 5 min stale time, no refetch-on-focus, 1 retry). Custom hooks (`useGovernance.ts`, `useDataManagement.ts`) wrap query/mutation logic per feature.
- **Components**:
  - `layout/` — `AppLayout`, `SidebarNavigation`, `TopBar`, `AppearanceMenu` (theme + logo settings)
  - `charts/` — `BarChartCard`, `LineChartCard` (Recharts)
  - `tables/` — `ExceptionTable`, plus shared `ui/VirtualTable` for large lists
  - `cards/` — `KpiCard`
  - `ui/` — `Button`, `Table`, `PageSkeleton`, `ThemeToggle`, `VirtualTable`
  - `widgets/` — `GovernanceWidget` (renders role-gated governance telemetry)
- **Context**: `context/ThemeContext.tsx` (light/dark/system, `localStorage` key `hr-dashboard-theme`, syncs `document.documentElement.classList`), `context/BrandingContext.tsx` (logo upload, `localStorage` key `hr-dashboard-logo`).

## 9. Authentication & RBAC

Implemented in `backend/app/core/security.py` and `backend/app/api/dependencies/auth.py`:

- **Roles**: `SYSTEM_ADMIN`, `HR_ANALYST`, `EXECUTIVE` (enum).
- **Users**: a hardcoded `MOCK_USER_DB` with one synthetic account per role (`admin@synthetic.local`, `hr@synthetic.local`, `exec@synthetic.local`) — no real accounts, by design.
- **Login**: `POST /api/governance/token` (OAuth2 password flow) validates against the mock DB and returns an HS256 JWT (30-minute expiry, `sub` = email).
- **Protection**: `RoleChecker([...])` FastAPI dependency validates the bearer token and required role; used on `GET /api/governance/status` (SYSTEM_ADMIN + EXECUTIVE only — HR_ANALYST gets `403`, no token gets `401`).
- **Frontend**: `useLoginMutation()` posts credentials, stores the JWT in `localStorage`, and invalidates the governance-status query on success; `GovernanceWidget` renders "Access Denied (Fail Closed)" when unauthorized.

This is the only real auth in the app — all other analytical endpoints are currently open (no token required), matching the project's local-first, single-user posture.

## 10. Data Pipeline & dbt

**Scripts** (`scripts/`): `generate_sample_data.py` (synthetic data w/ intentional errors) → `ingest_raw.py` (Polars: CSV → bronze/silver Parquet) → dbt run via `build_warehouse.py` (bronze/silver → DuckDB warehouse) → `validate_data.py` (schema/business-rule checks, control-total reconciliation) → `refresh_all.py` (orchestrates all of the above). Additional scripts support the synthetic governance simulation (dry-run manifests, authorization-evidence validation, control-total reconciliation for the fictitious "controlled load").

**dbt project** (`dbt_analytics/`): DuckDB adapter, `profiles.yml` target `dev` pointing at `../warehouse/hr_analytics.duckdb`, all models materialized as **views**.
- `models/staging/` — 23 `stg_*` models: typed/cleaned per-source views (employees, payroll, attendance, recruitment, candidates, interviews, offers, onboarding, compliance, ER, career paths, talent reviews, succession, goals, learning, skills, competencies, HR requests, data quality, training catalog, vacancy requests, workforce plan).
- `models/marts/` — 134 `base_*`/`mart_*` models: canonical deduplicated bases (e.g. `base_active_workforce`) feeding domain KPI marts (`mart_exec_kpis`, `mart_payroll_kpis`, …) and Command Center marts.
- **157 SQL models total.**
- Business parameters (report month, SLA-day thresholds, grace period, critical job titles, etc.) are dbt variables in `dbt_project.yml`, not hardcoded in SQL.

## 11. Deployment

`docker-compose.yml` runs two services:

| Service | Build | Port | Notes |
|---|---|---|---|
| `hr-backend` | `backend/Dockerfile` (python:3.11-slim, non-root `appuser`) | `8000:8000` | Mounts `warehouse/`, `data/`, `scripts/`, `dbt_analytics/`, `config/`; healthcheck `curl /health`; optional S3 env vars (`AWS_*`) for DuckDB `httpfs` |
| `hr-frontend` | `frontend/Dockerfile` (Node 22 Alpine build → Nginx Alpine serve) | `8080:8080` | Build arg `VITE_API_URL`; `depends_on: backend` (`service_healthy`) |

Local (non-Docker) dev: Python venv + `uvicorn app.main:app --reload` (backend, port 8000) and `npm run dev` (frontend, Vite port 5173). See [README.md](README.md) for exact commands.

## 12. Governance & Synthetic-Data Rules

A large parallel body of work (`docs/*GATE*`, `docs/CONTROLLED_LOAD_*`, `config/gate_*`, `config/controlled_load_*`, the `/api/governance/status` endpoint, `GovernanceWidget`) simulates a 5-gate approval process an organization might use before loading *real* HR data: scope sign-off → field-mapping approval → privacy/security review → synthetic dry-run validation → controlled real-data-load authorization.

Hard rules (from `AGENTS.md`), binding on all contributors/agents:
- No real HR employee data may ever be accessed, requested, created, or loaded.
- No live system connections; no credentials/tokens/secrets committed.
- `data/real_*` may not be modified except its `.gitkeep` placeholders.
- No real-data load, scheduling, or communication may actually be executed/sent — it's all simulated.
- Human review required before merge.

## 13. Testing

| Layer | Tool | Location | Coverage |
|---|---|---|---|
| Backend | Pytest | `backend/tests/` (`test_auth.py`, `test_data.py`, `test_governance.py`) | JWT issuance/validation, RBAC (403/401 paths), data upload/refresh, governance status |
| Frontend unit | Vitest + React Testing Library | `frontend/src/**/*.test.tsx` (e.g. `GovernanceWidget.test.tsx`) | Component-level rendering/behavior |
| Frontend E2E | Playwright | `frontend/e2e/governance.spec.ts` | Fail-closed landing page, HR Analyst 403 flow, System Admin login → telemetry grid |

CI (`.github/workflows/ci-cd-pipeline.yml`) runs three gated jobs on every push/PR to `main`: **lint & typecheck** (oxlint, tsc, flake8) → **test suite** (Vitest, full data-pipeline refresh, Pytest) → **Docker build verification** (both images, cached via GitHub Actions cache).

## 14. Configuration

`config/` holds ~66 YAML files split between:
- **Real business logic** actually consumed by dbt/backend: `metrics_dictionary.yml`, `business_rules.yml` (SLA days, grace period, weekend days, critical titles, variance thresholds).
- **Synthetic-governance scaffolding**: per-gate sign-off status, risk registers, field-level access matrices, privacy/masking rules, control-total specs, dry-run manifests, incident-response/rollback plans — all inputs to the simulated approval workflow described in §12.

## 15. Known Limitations

- Leave/holiday exclusions are structurally supported in the attendance model but inactive (no source table yet).
- Recruitment trend charts overlay two simulated historical periods for MVP visuals; only the current period is live data (documented in `docs/DECISIONS.md`).
- Only the governance-status endpoint is auth-protected; all other analytical endpoints are open.
- No production deployment target exists — Docker Compose is for local use only.

## 16. Relationship to Existing Docs

- [`README.md`](README.md) / [`PROJECT_BRIEF.md`](PROJECT_BRIEF.md) — original Milestone-1 quick-start and scope; commands still valid but the "out of scope" list (Docker, RBAC) is now implemented.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) / [`docs/DECISIONS.md`](docs/DECISIONS.md) — data-flow diagram and the original rationale log for schema/metric decisions (still accurate for pipeline logic; predates dbt migration, RBAC, and theming).
- [`AGENTS.md`](AGENTS.md) — binding governance rules, unchanged and still in force.
- [`docs/`](docs) (remaining ~100 files) — the full synthetic Gate 1–5 governance paper trail referenced in §12.
- This file (`DOCUMENTATION.md`) is the current, consolidated reference across all of the above plus everything implemented since.

## 17. Versioning & Release Policy

**v1.0.0 "Genesis"** is the first production version of the HR Analytics Command Center. It is locked in place via two immutable references, both pushed to GitHub:

- **Tag `v1.0.0`** — an annotated git tag pinned permanently to this commit. Tags don't move; this snapshot is retrievable forever regardless of what happens on `main` afterward.
- **Branch `production`** — a long-lived branch that also points at this commit at release time. It exists so this release has a stable, checkout-able, deployable line of history independent of `main`'s future churn (e.g. `docker compose` can be built from `production` for a guaranteed-stable local deployment).

### Rule going forward

**All new work happens on `main` (via feature branches, as before) or dedicated feature branches — never directly on `production`.** `production` is only ever fast-forwarded to a new commit deliberately, when a future set of changes is reviewed and ready to become the *next* tagged release (e.g. `v1.1.0`). Until that happens, `production` and the `v1.0.0` tag stay frozen exactly as committed here, so this version can always be rebuilt/redeployed/rolled back to without any risk of accidentally picking up unfinished future work.

Practical implications:
- Bug fixes or new features → branch off `main`, PR/merge into `main` as usual.
- Ready to cut a new release → tag the chosen `main` commit (`vX.Y.Z`, with a name), then fast-forward/merge `production` to that same commit.
- Anyone who needs "the last known-good production build" checks out the `production` branch or the highest `vX.Y.Z` tag — never `main` directly, since `main` may be mid-flight on new work.
