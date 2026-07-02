from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.compliance import (
    ComplianceSummaryResponse,
    SaudizationSummaryResponse,
    SaudizationTrendItem,
    SaudizationByProjectResponse,
    SaudizationByProjectItem,
    SaudizationByDepartmentResponse,
    SaudizationByDepartmentItem,
    DocumentExpiryResponse,
    DocumentExpiryItem,
    GosiStatusResponse,
    GosiStatusItem,
    WpsStatusResponse,
    WpsStatusItem,
    ComplianceExceptionsResponse
)
from app.schemas.kpi import KPIItem, DQExceptionItem
import os
import yaml

router = APIRouter()

def get_configured_report_month(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:
        config_path = "config/business_rules.yml"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
        else:
            rules = {}
            
        compliance_rules = rules.get("compliance_rules", {})
        report_month_source = compliance_rules.get("report_month_source", "max_compliance_period")
        
        if report_month_source == "max_compliance_period":

            max_period_row = conn.execute("SELECT MAX(period) FROM compliance").fetchone()
            max_period = max_period_row[0] if max_period_row else None
            if max_period:
                return str(max_period)[:7]
        return "2026-06"
    except Exception:
        return "2026-06"


@router.get("/summary", response_model=ComplianceSummaryResponse)
def get_compliance_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_compliance_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No compliance KPI records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    report_month = get_configured_report_month()

    kpis = [
        KPIItem(
            key="saudization_pct",
            label="Saudization %",
            value=row_dict["saudization_pct"],
            unit="%",
            status="healthy" if row_dict["saudization_pct"] >= 30.0 else ("warning" if row_dict["saudization_pct"] >= 15.0 else "critical")
        ),
        KPIItem(
            key="saudi_headcount",
            label="Saudi Headcount",
            value=float(row_dict["saudi_headcount"]),
            unit="employees",
            status="neutral"
        ),
        KPIItem(
            key="non_saudi_headcount",
            label="Non-Saudi Headcount",
            value=float(row_dict["non_saudi_headcount"]),
            unit="employees",
            status="neutral"
        ),
        KPIItem(
            key="employees_missing_nationality",
            label="Employees Missing Nationality",
            value=float(row_dict["employees_missing_nationality"]),
            unit="employees",
            status="critical" if row_dict["employees_missing_nationality"] > 0 else "healthy"
        ),
        KPIItem(
            key="iqamas_expiring_30",
            label="Iqamas Expiring in 30 Days",
            value=float(row_dict["iqamas_expiring_30"]),
            unit="documents",
            status="warning" if row_dict["iqamas_expiring_30"] > 0 else "healthy"
        ),
        KPIItem(
            key="work_permits_expiring_30",
            label="Work Permits Expiring in 30 Days",
            value=float(row_dict["work_permits_expiring_30"]),
            unit="documents",
            status="warning" if row_dict["work_permits_expiring_30"] > 0 else "healthy"
        ),
        KPIItem(
            key="iqamas_expired",
            label="Expired Iqamas",
            value=float(row_dict["iqamas_expired"]),
            unit="documents",
            status="critical" if row_dict["iqamas_expired"] > 0 else "healthy"
        ),
        KPIItem(
            key="work_permits_expired",
            label="Expired Work Permits",
            value=float(row_dict["work_permits_expired"]),
            unit="documents",
            status="critical" if row_dict["work_permits_expired"] > 0 else "healthy"
        ),
        KPIItem(
            key="gosi_missing_count",
            label="GOSI Missing / Not Registered Count",
            value=float(row_dict["gosi_missing_count"]),
            unit="employees",
            status="critical" if row_dict["gosi_missing_count"] > 0 else "healthy"
        ),
        KPIItem(
            key="wps_exception_count",
            label="WPS Exception Count",
            value=float(row_dict["wps_exception_count"]),
            unit="employees",
            status="critical" if row_dict["wps_exception_count"] > 0 else "healthy"
        ),
        KPIItem(
            key="compliance_exception_count",
            label="Compliance Exception Count",
            value=float(row_dict["compliance_exception_count"]),
            unit="issues",
            status="critical" if row_dict["compliance_exception_count"] > 0 else "healthy"
        )
    ]

    return ComplianceSummaryResponse(report_month=report_month, kpis=kpis)

@router.get("/saudization", response_model=SaudizationSummaryResponse)
def get_saudization(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_saudization_summary ORDER BY period ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    trends = []
    for row in res:
        row_dict = dict(zip(cols, row))
        trends.append(SaudizationTrendItem(
            period=row_dict["period"],
            saudi_headcount=int(row_dict["saudi_headcount"]),
            non_saudi_headcount=int(row_dict["non_saudi_headcount"]),
            employees_missing_nationality=int(row_dict["employees_missing_nationality"]),
            saudization_pct=float(row_dict["saudization_pct"])
        ))
    return SaudizationSummaryResponse(trends=trends)

@router.get("/saudization-by-project", response_model=SaudizationByProjectResponse)
def get_saudization_by_project(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_saudization_by_project ORDER BY project ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    projects = []
    for row in res:
        row_dict = dict(zip(cols, row))
        projects.append(SaudizationByProjectItem(
            project=row_dict["project"],
            saudi_headcount=int(row_dict["saudi_headcount"]),
            non_saudi_headcount=int(row_dict["non_saudi_headcount"]),
            employees_missing_nationality=int(row_dict["employees_missing_nationality"]),
            total_headcount=int(row_dict["total_headcount"]),
            saudization_pct=float(row_dict["saudization_pct"])
        ))
    return SaudizationByProjectResponse(projects=projects)

@router.get("/saudization-by-department", response_model=SaudizationByDepartmentResponse)
def get_saudization_by_department(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_saudization_by_department ORDER BY department ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    departments = []
    for row in res:
        row_dict = dict(zip(cols, row))
        departments.append(SaudizationByDepartmentItem(
            department=row_dict["department"],
            saudi_headcount=int(row_dict["saudi_headcount"]),
            non_saudi_headcount=int(row_dict["non_saudi_headcount"]),
            employees_missing_nationality=int(row_dict["employees_missing_nationality"]),
            total_headcount=int(row_dict["total_headcount"]),
            saudization_pct=float(row_dict["saudization_pct"])
        ))
    return SaudizationByDepartmentResponse(departments=departments)

@router.get("/document-expiry", response_model=DocumentExpiryResponse)
def get_document_expiry(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_document_expiry").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    buckets = []
    for row in res:
        row_dict = dict(zip(cols, row))
        buckets.append(DocumentExpiryItem(
            expiry_bucket=row_dict["expiry_bucket"],
            iqama_count=int(row_dict["iqama_count"]),
            work_permit_count=int(row_dict["work_permit_count"])
        ))
    return DocumentExpiryResponse(buckets=buckets)

@router.get("/gosi", response_model=GosiStatusResponse)
def get_gosi(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_gosi_status ORDER BY gosi_status ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    statuses = []
    for row in res:
        row_dict = dict(zip(cols, row))
        statuses.append(GosiStatusItem(
            gosi_status=row_dict["gosi_status"],
            employee_count=int(row_dict["employee_count"])
        ))
    return GosiStatusResponse(statuses=statuses)

@router.get("/wps", response_model=WpsStatusResponse)
def get_wps(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_wps_status ORDER BY wps_status ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    statuses = []
    for row in res:
        row_dict = dict(zip(cols, row))
        statuses.append(WpsStatusItem(
            wps_status=row_dict["wps_status"],
            headcount=int(row_dict["headcount"])
        ))
    return WpsStatusResponse(statuses=statuses)

@router.get("/exceptions", response_model=ComplianceExceptionsResponse)
def get_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_compliance_exceptions").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    exceptions = []
    for row in res:
        row_dict = dict(zip(cols, row))
        exceptions.append(DQExceptionItem(
            employee_id=row_dict["employee_id"],
            employee_name=row_dict["employee_name"] or "Unknown Employee",
            issue_type=row_dict["issue_type"],
            description=row_dict["description"],
            severity=row_dict["severity"],
            recommended_action=row_dict["recommended_action"]
        ))
    return ComplianceExceptionsResponse(exceptions=exceptions)
