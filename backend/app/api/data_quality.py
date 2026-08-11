from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.kpi import DataQualitySummaryResponse, DQExceptionsResponse, DQExceptionItem
from app.api._provenance import Provenance, get_provenance, suppressible

router = APIRouter()

@router.get("/summary", response_model=DataQualitySummaryResponse)
def get_data_quality_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    # Column mode: @suppressible does not run here, so the coverage of
    # every domain this mart reads is noted explicitly. The KPI strip is
    # the most-read surface and the one carrying the em dash, so it is
    # the last place a coverage note should be missing.
    prov.note_coverage("mart_data_quality_summary")
    try:

        res = conn.execute("SELECT * FROM mart_data_quality_summary").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No data quality summary records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

    # Column mode: each counter is nulled on its own. data_quality_score is
    # scope_to_provided (ruling 1) and passes through; scoping it to the
    # provided domains is step 4.
    mart = "mart_data_quality_summary"
    return DataQualitySummaryResponse(
        data_quality_score=prov.value(
            mart, "data_quality_score",
            round(row_dict["data_quality_score"] * 100, 2)),
        missing_manager_count=prov.value(
            mart, "missing_manager_count", row_dict["missing_manager_count"]),
        missing_project_count=prov.value(
            mart, "missing_project_count", row_dict["missing_project_count"]),
        missing_cost_center_count=prov.value(
            mart, "missing_cost_center_count", row_dict["missing_cost_center_count"]),
        missing_nationality_count=prov.value(
            mart, "missing_nationality_count", row_dict["missing_nationality_count"]),
        duplicate_employee_count=prov.value(
            mart, "duplicate_employee_count", row_dict["duplicate_employee_count"]),
        invalid_payroll_count=prov.value(
            mart, "invalid_payroll_count", row_dict["invalid_payroll_count"]),
        suppressed=prov.block(),
        coverage_notes=prov.coverage_block()
    )

@router.get("/exceptions", response_model=DQExceptionsResponse)
@suppressible(DQExceptionsResponse, "mart_data_quality_exceptions")
def get_data_quality_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_data_quality_exceptions").fetchall()
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
