from fastapi import APIRouter, HTTPException
from app.db.duckdb_client import DuckDBClient
from app.schemas.er import (
    ErSummaryResponse,
    ErTrendResponse,
    ErTrendItem,
    ErCasesByProjectResponse,
    ErCasesByProjectItem,
    ErCasesByDepartmentResponse,
    ErCasesByDepartmentItem,
    ErCaseTypeResponse,
    ErCaseTypeItem,
    ErCaseStatusResponse,
    ErCaseStatusItem,
    ErSlaPerformanceResponse,
    ErSlaPerformanceItem,
    ErAgingBucketResponse,
    ErAgingBucketItem,
    ErExceptionsResponse
)
from app.schemas.kpi import KPIItem, DQExceptionItem
import os
import yaml

router = APIRouter()

def get_configured_report_month():
    conn = None
    try:
        config_path = "config/business_rules.yml"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)
        else:
            rules = {}
            
        er_rules = rules.get("er_rules", {})
        report_month_source = er_rules.get("report_month_source", "max_case_date")
        
        if report_month_source == "max_case_date":
            conn = DuckDBClient.get_connection()
            max_date_row = conn.execute("SELECT MAX(created_date) FROM employee_relations").fetchone()
            max_date = max_date_row[0] if max_date_row else None
            if max_date:
                return str(max_date)[:7]
        return "2026-06"
    except Exception:
        return "2026-06"
    finally:
        if conn:
            conn.close()

@router.get("/summary", response_model=ErSummaryResponse)
def get_er_summary():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No ER KPI records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    report_month = get_configured_report_month()

    kpis = [
        KPIItem(
            key="total_open_er_cases",
            label="Total Open ER Cases",
            value=float(row_dict["total_open_er_cases"]),
            unit="cases",
            status="critical" if row_dict["total_open_er_cases"] > 5 else "healthy"
        ),
        KPIItem(
            key="new_cases_this_month",
            label="New Cases This Month",
            value=float(row_dict["new_cases_this_month"]),
            unit="cases",
            status="neutral"
        ),
        KPIItem(
            key="closed_cases_this_month",
            label="Closed Cases This Month",
            value=float(row_dict["closed_cases_this_month"]),
            unit="cases",
            status="neutral"
        ),
        KPIItem(
            key="average_case_aging_days",
            label="Average Case Aging Days",
            value=float(row_dict["average_case_aging_days"]),
            unit="days",
            status="warning" if row_dict["average_case_aging_days"] > 14 else "healthy"
        ),
        KPIItem(
            key="overdue_cases",
            label="Overdue Cases",
            value=float(row_dict["overdue_cases"]),
            unit="cases",
            status="critical" if row_dict["overdue_cases"] > 0 else "healthy"
        ),
        KPIItem(
            key="sla_compliance_pct",
            label="SLA Compliance %",
            value=float(row_dict["sla_compliance_pct"]),
            unit="%",
            status="healthy" if row_dict["sla_compliance_pct"] >= 90.0 else ("warning" if row_dict["sla_compliance_pct"] >= 75.0 else "critical")
        ),
        KPIItem(
            key="disciplinary_cases",
            label="Disciplinary Cases",
            value=float(row_dict["disciplinary_cases"]),
            unit="cases",
            status="neutral"
        ),
        KPIItem(
            key="grievance_cases",
            label="Grievance Cases",
            value=float(row_dict["grievance_cases"]),
            unit="cases",
            status="neutral"
        ),
        KPIItem(
            key="labor_cases",
            label="Labor Cases",
            value=float(row_dict["labor_cases"]),
            unit="cases",
            status="neutral"
        ),
        KPIItem(
            key="escalated_cases",
            label="Escalated Cases",
            value=float(row_dict["escalated_cases"]),
            unit="cases",
            status="warning" if row_dict["escalated_cases"] > 0 else "healthy"
        ),
        KPIItem(
            key="er_exception_count",
            label="ER Exception Count",
            value=float(row_dict["er_exception_count"]),
            unit="issues",
            status="critical" if row_dict["er_exception_count"] > 0 else "healthy"
        )
    ]

    return ErSummaryResponse(report_month=report_month, kpis=kpis)

@router.get("/trends", response_model=ErTrendResponse)
def get_er_trends():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_case_trend ORDER BY period ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    trends = []
    for row in res:
        row_dict = dict(zip(cols, row))
        trends.append(ErTrendItem(
            period=row_dict["period"],
            new_cases=int(row_dict["new_cases"]),
            closed_cases=int(row_dict["closed_cases"])
        ))
    return ErTrendResponse(trends=trends)

@router.get("/by-project", response_model=ErCasesByProjectResponse)
def get_er_by_project():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_cases_by_project ORDER BY project ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    projects = []
    for row in res:
        row_dict = dict(zip(cols, row))
        projects.append(ErCasesByProjectItem(
            project=row_dict["project"],
            total_cases=int(row_dict["total_cases"]),
            open_cases=int(row_dict["open_cases"]),
            closed_cases=int(row_dict["closed_cases"]),
            escalated_cases=int(row_dict["escalated_cases"]),
            compliant_cases=int(row_dict["compliant_cases"]),
            compliance_pct=float(row_dict["compliance_pct"])
        ))
    return ErCasesByProjectResponse(projects=projects)

@router.get("/by-department", response_model=ErCasesByDepartmentResponse)
def get_er_by_department():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_cases_by_department ORDER BY department ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    departments = []
    for row in res:
        row_dict = dict(zip(cols, row))
        departments.append(ErCasesByDepartmentItem(
            department=row_dict["department"],
            total_cases=int(row_dict["total_cases"]),
            open_cases=int(row_dict["open_cases"]),
            closed_cases=int(row_dict["closed_cases"]),
            escalated_cases=int(row_dict["escalated_cases"]),
            compliant_cases=int(row_dict["compliant_cases"]),
            compliance_pct=float(row_dict["compliance_pct"])
        ))
    return ErCasesByDepartmentResponse(departments=departments)

@router.get("/case-types", response_model=ErCaseTypeResponse)
def get_er_case_types():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_case_type_distribution ORDER BY case_type ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    case_types = []
    for row in res:
        row_dict = dict(zip(cols, row))
        case_types.append(ErCaseTypeItem(
            case_type=row_dict["case_type"],
            case_count=int(row_dict["case_count"])
        ))
    return ErCaseTypeResponse(case_types=case_types)

@router.get("/status", response_model=ErCaseStatusResponse)
def get_er_status():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_case_status_distribution ORDER BY case_status ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    statuses = []
    for row in res:
        row_dict = dict(zip(cols, row))
        statuses.append(ErCaseStatusItem(
            case_status=row_dict["case_status"],
            case_count=int(row_dict["case_count"])
        ))
    return ErCaseStatusResponse(statuses=statuses)

@router.get("/sla", response_model=ErSlaPerformanceResponse)
def get_er_sla():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_sla_performance ORDER BY category_type ASC, category ASC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    performance = []
    for row in res:
        row_dict = dict(zip(cols, row))
        performance.append(ErSlaPerformanceItem(
            category_type=row_dict["category_type"],
            category=row_dict["category"],
            eligible_count=int(row_dict["eligible_count"]),
            compliant_count=int(row_dict["compliant_count"]),
            breached_count=int(row_dict["breached_count"]),
            compliance_pct=float(row_dict["compliance_pct"])
        ))
    return ErSlaPerformanceResponse(performance=performance)

@router.get("/aging", response_model=ErAgingBucketResponse)
def get_er_aging():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_aging_buckets").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    buckets = []
    for row in res:
        row_dict = dict(zip(cols, row))
        buckets.append(ErAgingBucketItem(
            aging_bucket=row_dict["aging_bucket"],
            case_count=int(row_dict["case_count"])
        ))
    return ErAgingBucketResponse(buckets=buckets)

@router.get("/exceptions", response_model=ErExceptionsResponse)
def get_er_exceptions():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_er_exceptions").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    exceptions = []
    for row in res:
        row_dict = dict(zip(cols, row))
        exceptions.append(DQExceptionItem(
            employee_id=row_dict["case_id"],
            employee_name=row_dict["employee_name"] or "Unknown Employee",
            issue_type=row_dict["issue_type"],
            description=row_dict["description"],
            severity=row_dict["severity"],
            recommended_action=row_dict["recommended_action"]
        ))
    return ErExceptionsResponse(exceptions=exceptions)
