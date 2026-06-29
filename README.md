# HR Analytics Command Center

A local-first, high-performance HR Analytics dashboard powered by Python, Polars, DuckDB, FastAPI, and React + TypeScript + Vite.

## Architecture

This application is built with a strict separation of concerns, keeping all official calculations out of the frontend and inside the DuckDB analytics views and Python services:
1. **Data Layer**: Raw CSVs (`data/sample/`) -> Ingestion/Parquet (`data/bronze/` & `data/silver/`) -> Validation (`data/gold/data_quality_report.parquet`) -> DuckDB Warehouse (`warehouse/hr_analytics.duckdb`).
2. **Backend**: FastAPI serving metrics directly from DuckDB view queries.
3. **Frontend**: React (Vite + TypeScript + Tailwind CSS) rendering Apache ECharts and TanStack Table based on backend API data.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js v18+ (npm v9+)

### Installation and Run Command Sequence

Follow these steps to initialize and run the app locally:

1. **Clone and Navigate**:
   ```bash
   cd c:/tmp/HR-DASHBOARD
   ```

2. **Setup Python Virtual Environment and Install Dependencies**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Run the Data Refresh Pipeline**:
   This script generates the fake sample data with intentional data quality issues, cleans it, validates it, and builds the DuckDB analytical warehouse:
   ```bash
   python scripts/refresh_all.py
   ```

4. **Start the FastAPI Backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
   The backend will be available at `http://127.0.0.1:8000`. You can check:
   - Health: `http://127.0.0.1:8000/health`
   - Executive Summary: `http://127.0.0.1:8000/api/executive/summary`
   - Data Quality: `http://127.0.0.1:8000/api/data-quality/summary`
   - Exceptions: `http://127.0.0.1:8000/api/data-quality/exceptions`
   - Metadata status: `http://127.0.0.1:8000/api/meta/refresh-status`

5. **Start the React Frontend**:
   Open a new terminal, navigate to the frontend directory:
   ```bash
   cd c:/tmp/HR-DASHBOARD/frontend
   npm install
   npm run dev
   ```
   Open `http://localhost:5173/` in your browser.
