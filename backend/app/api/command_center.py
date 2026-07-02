from fastapi import APIRouter, HTTPException, Depends
from typing import List
import os
import json
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.command_center import (
    CommandCenterOverviewResponse,
    ModuleHealthResponse,
    PriorityAlertResponse,
    ExceptionSummaryResponse,
    FreshnessResponse,
    FilterOptionsResponse,
    NavigationStatusResponse,
    QaIndexResponse,
    QaIndexItem
)

router = APIRouter()

@router.get("/overview", response_model=CommandCenterOverviewResponse)
def get_overview(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        row = conn.execute("SELECT * FROM mart_command_center_overview").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Overview metrics not found")
        
        desc = conn.execute("DESCRIBE mart_command_center_overview").fetchall()
        cols = [d[0] for d in desc]
        data = dict(zip(cols, row))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/module-health", response_model=ModuleHealthResponse)
def get_module_health(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT * FROM mart_command_center_module_health").fetchall()
        desc = conn.execute("DESCRIBE mart_command_center_module_health").fetchall()
        cols = [d[0] for d in desc]
        modules = [dict(zip(cols, row)) for row in rows]
        return {"modules": modules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/priority-alerts", response_model=PriorityAlertResponse)
def get_priority_alerts(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT * FROM mart_command_center_priority_alerts").fetchall()
        desc = conn.execute("DESCRIBE mart_command_center_priority_alerts").fetchall()
        cols = [d[0] for d in desc]
        alerts = [dict(zip(cols, row)) for row in rows]
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exceptions", response_model=ExceptionSummaryResponse)
def get_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT * FROM mart_command_center_exception_summary").fetchall()
        desc = conn.execute("DESCRIBE mart_command_center_exception_summary").fetchall()
        cols = [d[0] for d in desc]
        exceptions = [dict(zip(cols, row)) for row in rows]
        return {"exceptions": exceptions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-freshness", response_model=FreshnessResponse)
def get_data_freshness(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT * FROM mart_command_center_data_freshness").fetchall()
        desc = conn.execute("DESCRIBE mart_command_center_data_freshness").fetchall()
        cols = [d[0] for d in desc]
        freshness = [dict(zip(cols, row)) for row in rows]
        return {"freshness": freshness}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filter-options", response_model=FilterOptionsResponse)
def get_filter_options(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        row = conn.execute("SELECT * FROM mart_command_center_filter_options").fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Filter options not found")
        
        desc = conn.execute("DESCRIBE mart_command_center_filter_options").fetchall()
        cols = [d[0] for d in desc]
        data = dict(zip(cols, row))
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/navigation-status", response_model=NavigationStatusResponse)
def get_navigation_status(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT * FROM mart_command_center_navigation_status").fetchall()
        desc = conn.execute("DESCRIBE mart_command_center_navigation_status").fetchall()
        cols = [d[0] for d in desc]
        navigation = [dict(zip(cols, row)) for row in rows]
        return {"navigation": navigation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qa-index", response_model=QaIndexResponse)
def get_qa_index(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        rows = conn.execute("SELECT module_key, module_label, screenshot_path, qa_report_path FROM base_command_center_module_registry").fetchall()
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        
        qa_index = []
        for row in rows:
            m_key, m_label, scr_path, qa_path = row
            
            # Map specific paths used by milestones
            raw_api_path = f"docs/qa/api_outputs/milestone_2e_er_api_outputs.json" if m_key == 'er' else \
                           f"docs/qa/api_outputs/milestone_2f_recruitment_api_outputs.json" if m_key == 'recruitment' else \
                           f"docs/qa/api_outputs/milestone_2g_talent_api_outputs.json" if m_key == 'talent' else \
                           f"docs/qa/api_outputs/milestone_2b_payroll_api_outputs.json" if m_key == 'payroll' else \
                           f"docs/qa/api_outputs/milestone_2c_attendance_api_outputs.json" if m_key == 'attendance' else \
                           f"docs/qa/api_outputs/milestone_2d_compliance_api_outputs.json" if m_key == 'compliance' else \
                           f"docs/qa/api_outputs/{m_key}_api_outputs.json"
            
            abs_scr_path = os.path.join(project_root, scr_path)
            abs_qa_path = os.path.join(project_root, qa_path)
            abs_raw_path = os.path.join(project_root, raw_api_path)
            
            scr_exists = os.path.exists(abs_scr_path)
            qa_exists = os.path.exists(abs_qa_path)
            raw_exists = os.path.exists(abs_raw_path)
            
            status = "Complete" if (scr_exists and qa_exists and raw_exists) else "Pending"
            
            qa_index.append(QaIndexItem(
                module_key=m_key,
                module_label=m_label,
                screenshot_path=scr_path,
                screenshot_exists=scr_exists,
                qa_report_path=qa_path,
                qa_report_exists=qa_exists,
                raw_api_path=raw_api_path,
                raw_api_exists=raw_exists,
                status=status
            ))
            
        return {"qa_index": qa_index}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

