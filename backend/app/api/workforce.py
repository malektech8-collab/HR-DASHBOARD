from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.workforce import (
    WorkforceSummaryResponse, 
    WorkforceTrendsResponse, 
    WorkforceDistributionResponse, 
    ExpiryAgingResponse,
    CategoryDistribution
)
from app.schemas.kpi import KPIItem, DQExceptionsResponse, DQExceptionItem

router = APIRouter()

@router.get("/summary", response_model=WorkforceSummaryResponse)
def get_workforce_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_workforce_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No workforce KPI records found")
        
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    # Build KPIs list matching exactly the 10 KPIs requested
    kpis = [
        KPIItem(
            key="active_headcount",
            label="Active Headcount",
            value=row_dict["active_headcount"],
            unit="employees",
            trend_value=5.2,
            trend_direction="up",
            status="healthy"
        ),
        KPIItem(
            key="saudi_headcount",
            label="Saudi Headcount",
            value=row_dict["saudi_headcount"],
            unit="employees",
            trend_value=12.5,
            trend_direction="up",
            status="healthy"
        ),
        KPIItem(
            key="non_saudi_headcount",
            label="Non-Saudi Headcount",
            value=row_dict["non_saudi_headcount"],
            unit="employees",
            trend_value=0.0,
            trend_direction="flat",
            status="neutral"
        ),
        KPIItem(
            key="saudization_rate",
            label="Saudization Rate",
            value=round(row_dict["saudization_rate"] * 100, 2),
            unit="%",
            trend_value=2.4,
            trend_direction="up",
            status="healthy" if row_dict["saudization_rate"] >= 0.40 else "warning"
        ),
        KPIItem(
            key="probation_count",
            label="Employees on Probation",
            value=row_dict["probation_count"],
            unit="employees",
            status="neutral"
        ),
        KPIItem(
            key="contract_expiring_30",
            label="Contracts Expiring in 30 Days",
            value=row_dict["contract_expiring_30"],
            unit="contracts",
            status="warning" if row_dict["contract_expiring_30"] > 0 else "healthy"
        ),
        KPIItem(
            key="iqama_expiring_30",
            label="Iqamas Expiring in 30 Days",
            value=row_dict["iqama_expiring_30"],
            unit="iqamas",
            status="warning" if row_dict["iqama_expiring_30"] > 0 else "healthy"
        ),
        KPIItem(
            key="missing_manager_count",
            label="Missing Manager",
            value=row_dict["missing_manager_count"],
            unit="issues",
            status="warning" if row_dict["missing_manager_count"] > 0 else "healthy"
        ),
        KPIItem(
            key="missing_project_count",
            label="Missing Project",
            value=row_dict["missing_project_count"],
            unit="issues",
            status="warning" if row_dict["missing_project_count"] > 0 else "healthy"
        ),
        KPIItem(
            key="missing_cost_center_count",
            label="Missing Cost Center",
            value=row_dict["missing_cost_center_count"],
            unit="issues",
            status="warning" if row_dict["missing_cost_center_count"] > 0 else "healthy"
        )
    ]

    return WorkforceSummaryResponse(
        report_month="2026-06",
        kpis=kpis
    )

@router.get("/trends", response_model=WorkforceTrendsResponse)
def get_workforce_trends(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT month, active_headcount FROM mart_workforce_headcount_trend").fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    months = [r[0] for r in res]
    headcount = [r[1] for r in res]

    return WorkforceTrendsResponse(
        months=months,
        headcount_trend=headcount
    )

@router.get("/distribution", response_model=WorkforceDistributionResponse)
def get_workforce_distribution(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT category, metric_value, headcount FROM mart_workforce_distribution").fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    # Split rows into respective categories
    dist_dict = {
        "department": {"labels": [], "values": []},
        "project": {"labels": [], "values": []},
        "nationality_group": {"labels": [], "values": []},
        "employment_type": {"labels": [], "values": []},
        "status": {"labels": [], "values": []}
    }

    for r in res:
        cat = r[0]
        val = r[1]
        cnt = r[2]
        if cat in dist_dict:
            dist_dict[cat]["labels"].append(val)
            dist_dict[cat]["values"].append(cnt)

    return WorkforceDistributionResponse(
        department=CategoryDistribution(**dist_dict["department"]),
        project=CategoryDistribution(**dist_dict["project"]),
        nationality_group=CategoryDistribution(**dist_dict["nationality_group"]),
        employment_type=CategoryDistribution(**dist_dict["employment_type"]),
        status=CategoryDistribution(**dist_dict["status"])
    )

@router.get("/contract-expiry", response_model=ExpiryAgingResponse)
def get_contract_expiry(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_workforce_contract_expiry").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No contract expiry records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    return ExpiryAgingResponse(
        expired=row_dict["expired"],
        bucket_0_30=row_dict["0_30"],
        bucket_31_60=row_dict["31_60"],
        bucket_61_90=row_dict["61_90"],
        bucket_90_plus=row_dict["90_plus"],
        missing_date=row_dict["missing_date"]
    )

@router.get("/iqama-expiry", response_model=ExpiryAgingResponse)
def get_iqama_expiry(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_workforce_iqama_expiry").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No iqama expiry records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    return ExpiryAgingResponse(
        expired=row_dict["expired"],
        bucket_0_30=row_dict["0_30"],
        bucket_31_60=row_dict["31_60"],
        bucket_61_90=row_dict["61_90"],
        bucket_90_plus=row_dict["90_plus"],
        missing_date=row_dict["missing_date"]
    )

@router.get("/exceptions", response_model=DQExceptionsResponse)
def get_workforce_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection)):
    try:

        res = conn.execute("SELECT * FROM mart_workforce_exceptions").fetchall()
        exceptions = []
        for r in res:
            exceptions.append(DQExceptionItem(
                employee_id=r[0] if r[0] else "",
                employee_name=r[1] if r[1] else "",
                issue_type=r[2] if r[2] else "",
                description=r[3] if r[3] else "",
                severity=r[4] if r[4] else "",
                recommended_action=r[5] if r[5] else ""
            ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    return DQExceptionsResponse(exceptions=exceptions)
