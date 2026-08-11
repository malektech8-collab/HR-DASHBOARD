"""Shared report-month resolver (cycle 5a).

Single source of truth for the API: read the resolved reporting period straight
from the mart that dbt built from the injected `report_month` var
(`base_command_center_report_context`). This guarantees the API agrees with
every mart.

Replaces the 4 duplicated, dead `get_configured_report_month()` copies that
previously lived in attendance.py / compliance.py / er.py / recruitment.py.

Fallback policy (Phase 2 P0-3, step 2a.5)
-----------------------------------------
The fallback used to be `settings.DEFAULT_REPORT_MONTH` unconditionally. In
real mode that labels a client's numbers with a period this repository chose —
the same failure the pipeline resolver now aborts on, one layer up, where it is
even harder to notice because the label renders in the page header beside real
data. Real mode therefore honours an explicit REPORT_MONTH and otherwise fails
loudly; DEFAULT_REPORT_MONTH is demo-only. See scripts/report_period.py.
"""
import duckdb
from fastapi import Depends, HTTPException

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

    # The mart is unreadable or empty. An operator-set period is still an
    # explicit decision, so it is honoured in both modes.
    operator = str(settings.REPORT_MONTH or "").strip()
    if operator:
        return operator[:7]

    if str(settings.DATA_MODE or "demo").strip().lower() == "real":
        raise HTTPException(
            status_code=503,
            detail=(
                "The reporting period is unavailable: the warehouse has not "
                "been built, or it was built without one. Set REPORT_MONTH "
                "and re-run the pipeline. The API will not label real data "
                "with a default period."
            ),
        )

    return settings.DEFAULT_REPORT_MONTH
