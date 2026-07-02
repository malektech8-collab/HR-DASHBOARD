# Local Demo Runbook

This guide details how to launch and demonstrate the HR Analytics Command Center locally in synthetic mode.

## Prerequisites
- Python 3.10+
- Node.js 18+

## Startup Steps

### 1. Initialize & Refresh the DuckDB Warehouse
Run the pipeline setup script to populate the local sandbox warehouse with synthetic data:
```bash
python scripts/refresh_warehouse.py
```
This writes mock records to `data/hr_analytics_sandbox.db`.

### 2. Run the Backend API
Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
Verify the API is running by visiting `http://localhost:8000/docs`.

### 3. Run the Frontend UI
Start the development server for the frontend dashboard:
```bash
npm install
npm run dev
```
Open `http://localhost:5173` to view the dashboard.

### 4. Execute the Test Suite
Ensure all synthetic data constraints and governance checks pass:
```bash
pytest tests/
```

## Explaining the System State to Stakeholders
When demonstrating the application:
1. Point to the **Governance Lock Widget** in the sidebar.
2. Note that all keys (CHRO, CISO, IT Ops) are in the **Hold** or **Not Approved** state.
3. Explain that this state disables all live database connections, external APIs, and production endpoints.
4. Show that the charts are driven entirely by local synthetic data generated in Step 1.
