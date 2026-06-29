from fastapi import APIRouter, HTTPException
from app.db.duckdb_client import DuckDBClient
from app.schemas.kpi import DataQualitySummaryResponse, DQExceptionsResponse, DQExceptionItem

router = APIRouter()

@router.get("/summary", response_model=DataQualitySummaryResponse)
def get_data_quality_summary():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_data_quality_summary").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No data quality summary records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()
            
    return DataQualitySummaryResponse(
        data_quality_score=round(row_dict["data_quality_score"] * 100, 2),
        missing_manager_count=row_dict["missing_manager_count"],
        missing_project_count=row_dict["missing_project_count"],
        missing_cost_center_count=row_dict["missing_cost_center_count"],
        missing_nationality_count=row_dict["missing_nationality_count"],
        duplicate_employee_count=row_dict["duplicate_employee_count"],
        invalid_payroll_count=row_dict["invalid_payroll_count"]
    )

@router.get("/exceptions", response_model=DQExceptionsResponse)
def get_data_quality_exceptions():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
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
    finally:
        if conn:
            conn.close()
            
    return DQExceptionsResponse(exceptions=exceptions)
