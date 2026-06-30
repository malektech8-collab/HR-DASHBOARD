# Developer & Admin Runbook

## System Requirements

- Python 3.10+
- Node.js 18+
- DuckDB CLI (Optional, for warehouse querying)

## Setup & Ingestion Pipeline

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```
2. **Warehouse Refresh**:
   To ingest synthetic source files, apply data quality checks, and rebuild analytical views, run:
   ```bash
   python scripts/refresh_all.py
   ```
3. **Database File**:
   Rebuilt DuckDB database is generated at `warehouse/hr_analytics.duckdb`.

## Launching Services

1. **FastAPI Backend**:
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. **Vite Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Verifying Governance Controls

1. **Backend Verification**:
   Run the static governance test:
   ```bash
   .venv\Scripts\python.exe -m pytest backend/tests/test_governance.py
   ```
2. **Synthetic Evidence Validator**:
   ```bash
   .venv\Scripts\python.exe scripts/validate_synthetic_authorization_evidence.py
   ```
3. **Audit Verification**:
   Scan staging folders:
   ```bash
   .venv\Scripts\python.exe scripts/audit_no_real_data_in_dry_run.py
   ```
