from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.kpi import ExecutiveSummaryResponse, KPIItem
from app.config import settings
import os
from datetime import datetime

router = APIRouter()

@router.get("/summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        # Query mart_exec_kpis
        res_kpi = conn.execute("SELECT * FROM mart_exec_kpis").fetchone()
        if not res_kpi:
            raise HTTPException(status_code=404, detail="No executive KPI records found")
        
        # Get column names
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res_kpi))
        
        # Query trends
        trends_res = conn.execute("SELECT month, active_headcount, payroll_cost FROM mart_exec_trends").fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    # Calculate last refresh time from DB modification time
    last_refresh_str = "Unknown"
    if os.path.exists(settings.DATABASE_PATH):
        mtime = os.path.getmtime(settings.DATABASE_PATH)
        # Formatted cleanly
        last_refresh_str = datetime.fromtimestamp(mtime).isoformat()
        
    # Build KPIs list
    kpis = [
        KPIItem(
            key="active_headcount",
            label="Active Headcount",
            value=row_dict["active_headcount"],
            unit="employees",
            trend_value=5.2,
            trend_direction="up",
            status="healthy" if row_dict["data_quality_score"] > 0.9 else "warning"
        ),
        KPIItem(
            key="joiners_this_month",
            label="Joiners This Month",
            value=row_dict["joiners_count"],
            unit="employees",
            trend_value=12.0,
            trend_direction="up",
            status="neutral"
        ),
        KPIItem(
            key="leavers_this_month",
            label="Leavers This Month",
            value=row_dict["leavers_count"],
            unit="employees",
            trend_value=0.0,
            trend_direction="flat",
            status="neutral"
        ),
        KPIItem(
            key="turnover_rate",
            label="Turnover Rate",
            value=round(row_dict["turnover_rate"] * 100, 2),
            unit="%",
            trend_value=-1.1,
            trend_direction="down",
            status="healthy" if row_dict["turnover_rate"] < 0.05 else "warning"
        ),
        KPIItem(
            key="payroll_cost",
            label="Payroll Cost",
            value=row_dict["payroll_cost"],
            unit="SAR",
            trend_value=1.8,
            trend_direction="up",
            status="neutral"
        ),
        KPIItem(
            key="overtime_cost",
            label="Overtime Cost",
            value=row_dict["overtime_cost"],
            unit="SAR",
            trend_value=25.4,
            trend_direction="up",
            status="warning" if row_dict["overtime_cost"] > 1000 else "healthy"
        ),
        KPIItem(
            key="absence_days",
            label="Absence Days",
            value=row_dict["absence_days"],
            unit="days",
            trend_value=-15.0,
            trend_direction="down",
            status="healthy" if row_dict["absence_days"] < 5 else "warning"
        ),
        KPIItem(
            key="data_quality_score",
            label="Data Quality Score",
            value=round(row_dict["data_quality_score"] * 100, 2),
            unit="%",
            trend_value=2.5,
            trend_direction="up",
            status="healthy" if row_dict["data_quality_score"] >= 0.90 else "critical"
        )
    ]
    
    # Prepare charts data
    headcount_trend = []
    payroll_trend = []
    months = []
    for r in trends_res:
        months.append(r[0])
        headcount_trend.append(r[1])
        payroll_trend.append(r[2])
        
    charts = {
        "months": months,
        "headcount_trend": headcount_trend,
        "payroll_trend": payroll_trend
    }
    
    return ExecutiveSummaryResponse(
        report_month=row_dict["report_month"],
        last_refresh_at=last_refresh_str,
        kpis=kpis,
        charts=charts
    )
