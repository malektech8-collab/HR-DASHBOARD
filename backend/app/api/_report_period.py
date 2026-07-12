"""Shared report-month resolver (cycle 5a).

Single source of truth for the API: read the resolved reporting period straight
from the mart that dbt built from the injected `report_month` var
(`base_command_center_report_context`). This guarantees the API agrees with
every mart. The only fallback (DB unreadable / no row) is the ONE system-wide
default in config, so the API and the pipeline can never drift apart.

Replaces the 4 duplicated, dead `get_configured_report_month()` copies that
previously lived in attendance.py / compliance.py / er.py / recruitment.py.
"""
import duckdb
from fastapi import Depends

from app.db.duckdb_client import get_db_connection
from app.config import settings


def get_report_month(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)) -> str:
    try:
        row = conn.execute(
            "SELECT report_month FROM base_command_center_report_context"
        ).fetchone()
        if row and row[0]:
            return str(row[0])[:7]
    except Exception:
        pass
    return settings.DEFAULT_REPORT_MONTH
