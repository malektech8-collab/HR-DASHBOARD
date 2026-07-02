from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.payroll import (
    PayrollSummaryResponse,
    PayrollReconciliationResponse,
    PayrollTrendsResponse,
    PayrollTrendItem,
    PayrollByProjectResponse,
    PayrollByProjectItem,
    PayrollByDepartmentResponse,
    PayrollByDepartmentItem,
    PayrollComponentsResponse,
    PayrollComponentItem,
    PayrollVarianceResponse,
    PayrollComponentVarianceItem,
    PayrollEmployeeVarianceItem,
    PayrollExceptionsResponse
)
from app.schemas.kpi import KPIItem, DQExceptionItem
from typing import List

router = APIRouter()

@router.get("/summary", response_model=PayrollSummaryResponse)
def get_payroll_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No payroll KPI records found")
        kpis_cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(kpis_cols, res))
        
        recon_res = conn.execute("SELECT * FROM mart_payroll_reconciliation").fetchone()
        if not recon_res:
            raise HTTPException(status_code=404, detail="No payroll reconciliation records found")
        recon_cols = [desc[0] for desc in conn.description]
        recon_dict = dict(zip(recon_cols, recon_res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    # Determine trend values
    variance_pct = row_dict["payroll_variance_pct"]
    trend_dir = "flat"
    if variance_pct > 0.001:
        trend_dir = "up"
    elif variance_pct < -0.001:
        trend_dir = "down"

    kpis = [
        KPIItem(
            key="total_payroll_cost",
            label="Total Payroll Cost",
            value=row_dict["total_payroll_cost"],
            unit="SAR",
            trend_value=round(abs(variance_pct) * 100, 2),
            trend_direction=trend_dir,
            status="warning" if abs(variance_pct) > 0.10 else "neutral"
        ),
        KPIItem(
            key="net_payroll",
            label="Net Payroll",
            value=row_dict["net_payroll"],
            unit="SAR",
            status="healthy"
        ),
        KPIItem(
            key="employees_paid",
            label="Employees Paid",
            value=row_dict["employees_paid"],
            unit="employees",
            status="healthy"
        ),
        KPIItem(
            key="avg_cost_per_employee",
            label="Average Cost per Employee",
            value=round(row_dict["avg_cost_per_employee"], 2),
            unit="SAR",
            status="neutral"
        ),
        KPIItem(
            key="payroll_variance_pct",
            label="Payroll Variance vs Previous Month",
            value=round(variance_pct * 100, 2),
            unit="%",
            trend_value=round(abs(variance_pct) * 100, 2),
            trend_direction=trend_dir,
            status="warning" if abs(variance_pct) > 0.10 else "healthy"
        ),
        KPIItem(
            key="basic_salary_cost",
            label="Basic Salary Cost",
            value=row_dict["basic_salary_cost"],
            unit="SAR",
            status="neutral"
        ),
        KPIItem(
            key="allowances_cost",
            label="Allowances Cost",
            value=row_dict["allowances_cost"],
            unit="SAR",
            status="neutral"
        ),
        KPIItem(
            key="overtime_cost",
            label="Overtime Cost",
            value=row_dict["overtime_cost"],
            unit="SAR",
            status="warning" if row_dict["overtime_cost"] > 10000 else "healthy"
        ),
        KPIItem(
            key="deductions",
            label="Deductions",
            value=row_dict["deductions"],
            unit="SAR",
            status="neutral"
        ),
        KPIItem(
            key="payroll_exception_count",
            label="Payroll Exception Count",
            value=row_dict["payroll_exception_count"],
            unit="issues",
            status="critical" if row_dict["payroll_exception_count"] > 0 else "healthy"
        )
    ]

    reconciliation = PayrollReconciliationResponse(
        total_gross_payroll=recon_dict["total_gross_payroll"],
        sum_displayed_components=recon_dict["sum_displayed_components"],
        unreconciled_component_difference=recon_dict["unreconciled_component_difference"],
        net_payroll=recon_dict["net_payroll"],
        gross_minus_deductions=recon_dict["gross_minus_deductions"],
        net_unreconciled_difference=recon_dict["net_unreconciled_difference"],
        project_payroll_total=recon_dict["project_payroll_total"],
        department_payroll_total=recon_dict["department_payroll_total"],
        employees_paid_count=recon_dict["employees_paid_count"],
        payroll_exception_count=recon_dict["payroll_exception_count"]
    )

    return PayrollSummaryResponse(
        report_month="2026-06",
        kpis=kpis,
        reconciliation=reconciliation
    )

@router.get("/trends", response_model=PayrollTrendsResponse)
def get_payroll_trends(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_trend ORDER BY month").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    trends = []
    for row in res:
        row_dict = dict(zip(cols, row))
        trends.append(PayrollTrendItem(
            month=row_dict["month"],
            total_payroll_cost=row_dict["total_payroll_cost"],
            basic_salary=row_dict["basic_salary"],
            allowances=row_dict["allowances"],
            overtime=row_dict["overtime"],
            deductions=row_dict["deductions"],
            net_payroll=row_dict["net_payroll"],
            headcount=row_dict["headcount"]
        ))

    return PayrollTrendsResponse(trends=trends)

@router.get("/by-project", response_model=PayrollByProjectResponse)
def get_payroll_by_project(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_by_project").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    projects = []
    for row in res:
        row_dict = dict(zip(cols, row))
        projects.append(PayrollByProjectItem(
            project=row_dict["project"],
            headcount=row_dict["headcount"],
            total_payroll_cost=row_dict["total_payroll_cost"],
            overtime_cost=row_dict["overtime_cost"]
        ))

    return PayrollByProjectResponse(projects=projects)

@router.get("/by-department", response_model=PayrollByDepartmentResponse)
def get_payroll_by_department(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_by_department").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    departments = []
    for row in res:
        row_dict = dict(zip(cols, row))
        departments.append(PayrollByDepartmentItem(
            department=row_dict["department"],
            headcount=row_dict["headcount"],
            total_payroll_cost=row_dict["total_payroll_cost"],
            overtime_cost=row_dict["overtime_cost"]
        ))

    return PayrollByDepartmentResponse(departments=departments)

@router.get("/components", response_model=PayrollComponentsResponse)
def get_payroll_components(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_components").fetchall()
        cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    components = []
    for row in res:
        row_dict = dict(zip(cols, row))
        components.append(PayrollComponentItem(
            component=row_dict["component"],
            amount=row_dict["amount"]
        ))

    return PayrollComponentsResponse(components=components)

@router.get("/variance", response_model=PayrollVarianceResponse)
def get_payroll_variance(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        # Query components variance
        comp_res = conn.execute("SELECT * FROM mart_payroll_variance_components").fetchall()
        comp_cols = [desc[0] for desc in conn.description]
        
        # Query employees variance
        emp_res = conn.execute("SELECT * FROM mart_payroll_variance_employees ORDER BY ABS(change_amount) DESC LIMIT 100").fetchall()
        emp_cols = [desc[0] for desc in conn.description]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    components = []
    for row in comp_res:
        row_dict = dict(zip(comp_cols, row))
        components.append(PayrollComponentVarianceItem(
            component=row_dict["component"],
            prev_amount=row_dict["prev_amount"],
            curr_amount=row_dict["curr_amount"],
            change_amount=row_dict["change_amount"],
            change_pct=row_dict["change_pct"]
        ))

    employees = []
    for row in emp_res:
        row_dict = dict(zip(emp_cols, row))
        employees.append(PayrollEmployeeVarianceItem(
            employee_id=row_dict["employee_id"],
            employee_name=row_dict["employee_name"],
            prev_amount=row_dict["prev_amount"],
            curr_amount=row_dict["curr_amount"],
            change_amount=row_dict["change_amount"],
            change_pct=row_dict["change_pct"]
        ))

    return PayrollVarianceResponse(components=components, employees=employees)

@router.get("/exceptions", response_model=PayrollExceptionsResponse)
def get_payroll_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_payroll_exceptions").fetchall()
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

    return PayrollExceptionsResponse(exceptions=exceptions)
