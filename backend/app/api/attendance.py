from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.attendance import (
    AttendanceSummaryResponse,
    AttendanceTrendsResponse,
    AttendanceTrendItem,
    AttendanceByProjectResponse,
    AttendanceByProjectItem,
    AttendanceByDepartmentResponse,
    AttendanceByDepartmentItem,
    AttendanceLateArrivalResponse,
    AttendanceLateArrivalItem,
    AttendanceOvertimeResponse,
    AttendanceOvertimeItem,
    AttendanceMissingPunchesResponse,
    AttendanceMissingPunchesItem,
    AttendanceExceptionsResponse
)
from app.schemas.kpi import KPIItem, DQExceptionItem
from app.api._report_period import get_report_month
from app.api._provenance import Provenance, get_provenance, suppressible

router = APIRouter()


def _pct_or_none(value):
    """Category F: a breakdown row's compliance can be NULL too."""
    return None if value is None else round(value * 100, 2)


@router.get("/summary", response_model=AttendanceSummaryResponse)
def get_attendance_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No attendance KPI records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    # Determine status and trends
    # Category F: NULL when no day in the period was reported on. Every
    # expression below has to tolerate it - a metric that cannot be measured
    # must not be turned into a number on the way out.
    compliance_pct = row_dict["attendance_compliance_pct"]

    def _pct(value):
        return None if value is None else round(value * 100, 2)
    
    kpis = prov.kpis("mart_attendance_kpis", [
        ("attendance_compliance_pct", lambda: KPIItem(
                key="attendance_compliance_pct",
                label="Attendance Compliance %",
                value=_pct(compliance_pct),
                unit="%",
                status="neutral" if compliance_pct is None else ("healthy" if compliance_pct >= 0.95 else ("warning" if compliance_pct >= 0.90 else "critical"))
            )),
        ("absence_days", lambda: KPIItem(
                key="absence_days",
                label="Absence Days",
                value=row_dict["absence_days"],
                unit="days",
                status="neutral" if row_dict["absence_days"] is None else ("warning" if row_dict["absence_days"] > 5 else "healthy")
            )),
        ("late_minutes", lambda: KPIItem(
                key="late_minutes",
                label="Late Minutes",
                value=row_dict["late_minutes"],
                unit="min",
                status="warning" if row_dict["late_minutes"] > 120 else "healthy"
            )),
        ("excused_late_minutes", lambda: KPIItem(
                key="excused_late_minutes",
                label="Excused Late Minutes",
                value=row_dict["excused_late_minutes"],
                unit="min",
                status="neutral"
            )),
        ("net_late_minutes", lambda: KPIItem(
                key="net_late_minutes",
                label="Net Late Minutes",
                value=row_dict["net_late_minutes"],
                unit="min",
                status="warning" if row_dict["net_late_minutes"] > 60 else "healthy"
            )),
        ("early_leave_minutes", lambda: KPIItem(
                key="early_leave_minutes",
                label="Early Leave Minutes",
                value=row_dict["early_leave_minutes"],
                unit="min",
                status="warning" if row_dict["early_leave_minutes"] > 120 else "healthy"
            )),
        ("missing_punch_count", lambda: KPIItem(
                key="missing_punch_count",
                label="Missing Punch Count",
                value=row_dict["missing_punch_count"],
                unit="punches",
                status="critical" if row_dict["missing_punch_count"] > 0 else "healthy"
            )),
        ("overtime_hours", lambda: KPIItem(
                key="overtime_hours",
                label="Overtime Hours",
                value=row_dict["overtime_hours"],
                unit="hrs",
                status="neutral"
            )),
        ("overtime_cost", lambda: KPIItem(
                key="overtime_cost",
                label="Overtime Cost",
                value=row_dict["overtime_cost"],
                unit="SAR",
                status="neutral"
            )),
        ("attendance_exception_count", lambda: KPIItem(
                key="attendance_exception_count",
                label="Attendance Exception Count",
                value=row_dict["attendance_exception_count"],
                unit="issues",
                status="critical" if row_dict["attendance_exception_count"] > 0 else "healthy"
            )),
    ])

    return AttendanceSummaryResponse(
        report_month=report_month,
        kpis=kpis,
        suppressed=prov.block()
    )

@router.get("/trends", response_model=AttendanceTrendsResponse)
@suppressible(AttendanceTrendsResponse, "mart_attendance_trend")
def get_attendance_trends(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_trend ORDER BY month").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    trends = []
    for row in res:
        row_dict = dict(zip(cols, row))
        trends.append(AttendanceTrendItem(
            month=row_dict["month"],
            attendance_compliance_pct=_pct_or_none(row_dict["attendance_compliance_pct"]),
            absence_days=row_dict["absence_days"],
            late_minutes=row_dict["late_minutes"],
            net_late_minutes=row_dict["net_late_minutes"],
            missing_punch_count=row_dict["missing_punch_count"],
            overtime_hours=row_dict["overtime_hours"]
        ))

    return AttendanceTrendsResponse(trends=trends)

@router.get("/by-project", response_model=AttendanceByProjectResponse)
@suppressible(AttendanceByProjectResponse, "mart_attendance_by_project")
def get_attendance_by_project(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_by_project").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    projects = []
    for row in res:
        row_dict = dict(zip(cols, row))
        projects.append(AttendanceByProjectItem(
            project=row_dict["project"],
            headcount=row_dict["headcount"],
            attendance_compliance_pct=_pct_or_none(row_dict["attendance_compliance_pct"]),
            absence_days=row_dict["absence_days"],
            late_minutes=row_dict["late_minutes"],
            missing_punches=row_dict["missing_punches"],
            overtime_hours=row_dict["overtime_hours"],
            overtime_cost=row_dict["overtime_cost"]
        ))

    return AttendanceByProjectResponse(projects=projects)

@router.get("/by-department", response_model=AttendanceByDepartmentResponse)
@suppressible(AttendanceByDepartmentResponse, "mart_attendance_by_department")
def get_attendance_by_department(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_by_department").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    departments = []
    for row in res:
        row_dict = dict(zip(cols, row))
        departments.append(AttendanceByDepartmentItem(
            department=row_dict["department"],
            headcount=row_dict["headcount"],
            attendance_compliance_pct=_pct_or_none(row_dict["attendance_compliance_pct"]),
            absence_days=row_dict["absence_days"],
            late_minutes=row_dict["late_minutes"],
            net_late_minutes=row_dict["net_late_minutes"],
            missing_punches=row_dict["missing_punches"],
            overtime_hours=row_dict["overtime_hours"],
            overtime_cost=row_dict["overtime_cost"]
        ))

    return AttendanceByDepartmentResponse(departments=departments)

@router.get("/late-arrival", response_model=AttendanceLateArrivalResponse)
@suppressible(AttendanceLateArrivalResponse, "mart_attendance_late_arrival")
def get_attendance_late_arrival(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_late_arrival ORDER BY total_late_minutes DESC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    late_arrivals = []
    for row in res:
        row_dict = dict(zip(cols, row))
        late_arrivals.append(AttendanceLateArrivalItem(
            employee_id=row_dict["employee_id"],
            employee_name=row_dict["employee_name"],
            department=row_dict["department"],
            project=row_dict["project"],
            total_late_minutes=row_dict["total_late_minutes"],
            total_excused_minutes=row_dict["total_excused_minutes"],
            total_net_late_minutes=row_dict["total_net_late_minutes"],
            late_arrival_incidents_count=row_dict["late_arrival_incidents_count"]
        ))

    return AttendanceLateArrivalResponse(late_arrivals=late_arrivals)

@router.get("/overtime", response_model=AttendanceOvertimeResponse)
@suppressible(AttendanceOvertimeResponse, "mart_attendance_overtime")
def get_attendance_overtime(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_overtime ORDER BY attendance_ot_hours DESC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    overtime_records = []
    for row in res:
        row_dict = dict(zip(cols, row))
        overtime_records.append(AttendanceOvertimeItem(
            employee_id=row_dict["employee_id"],
            employee_name=row_dict["employee_name"],
            department=row_dict["department"],
            project=row_dict["project"],
            attendance_ot_hours=row_dict["attendance_ot_hours"],
            payroll_ot_cost=row_dict["payroll_ot_cost"],
            reconciliation_status=row_dict["reconciliation_status"]
        ))

    return AttendanceOvertimeResponse(overtime_records=overtime_records)

@router.get("/missing-punches", response_model=AttendanceMissingPunchesResponse)
@suppressible(AttendanceMissingPunchesResponse, "mart_attendance_missing_punches")
def get_attendance_missing_punches(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_missing_punches ORDER BY total_missing_punches DESC").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    missing_punches = []
    for row in res:
        row_dict = dict(zip(cols, row))
        missing_punches.append(AttendanceMissingPunchesItem(
            employee_id=row_dict["employee_id"],
            employee_name=row_dict["employee_name"],
            department=row_dict["department"],
            project=row_dict["project"],
            missing_check_in_count=row_dict["missing_check_in_count"],
            missing_check_out_count=row_dict["missing_check_out_count"],
            total_missing_punches=row_dict["total_missing_punches"]
        ))

    return AttendanceMissingPunchesResponse(missing_punches=missing_punches)

@router.get("/exceptions", response_model=AttendanceExceptionsResponse)
@suppressible(AttendanceExceptionsResponse, "mart_attendance_exceptions")
def get_attendance_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_attendance_exceptions").fetchall()
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

    return AttendanceExceptionsResponse(exceptions=exceptions)
