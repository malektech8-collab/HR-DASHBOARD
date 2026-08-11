from fastapi import APIRouter, HTTPException, Depends
from app.db.duckdb_client import get_db_connection
import duckdb
from app.schemas.recruitment import (
    RecruitmentSummaryResponse,
    RecruitmentPipelineResponse,
    PipelineStageItem,
    RecruitmentTrendsResponse,
    RecruitmentTrendItem,
    RecruitmentByProjectResponse,
    RecruitmentByProjectItem,
    RecruitmentByDepartmentResponse,
    RecruitmentByDepartmentItem,
    TimeToFillResponse,
    TimeToFillItem,
    SourceEffectivenessResponse,
    SourceEffectivenessItem,
    OfferAcceptanceResponse,
    OfferAcceptanceItem,
    OnboardingStatusResponse,
    OnboardingStatusItem,
    WorkforcePlanVsActualResponse,
    WorkforcePlanVsActualItem,
    RecruitmentExceptionsResponse
)
from app.schemas.kpi import KPIItem, DQExceptionItem
from app.api._report_period import get_report_month
from app.api._provenance import Provenance, get_provenance, suppressible

router = APIRouter()



@router.get("/summary", response_model=RecruitmentSummaryResponse)
def get_recruitment_summary(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), report_month: str = Depends(get_report_month), prov: Provenance = Depends(get_provenance)):
    # Column mode: @suppressible does not run here, so the coverage of
    # every domain this mart reads is noted explicitly. The KPI strip is
    # the most-read surface and the one carrying the em dash, so it is
    # the last place a coverage note should be missing.
    prov.note_coverage("mart_recruitment_kpis")
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No recruitment KPI records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    kpis = prov.kpis("mart_recruitment_kpis", [
        ("open_requisitions", lambda: KPIItem(
                key="open_requisitions",
                label="Open Requisitions",
                value=float(row_dict["open_requisitions"]),
                unit="requisitions",
                status="neutral"
            )),
        ("approved_vacancies", lambda: KPIItem(
                key="approved_vacancies",
                label="Approved Vacancies",
                value=float(row_dict["approved_vacancies"]),
                unit="vacancies",
                status="neutral"
            )),
        ("candidates_in_pipeline", lambda: KPIItem(
                key="candidates_in_pipeline",
                label="Candidates in Pipeline",
                value=float(row_dict["candidates_in_pipeline"]),
                unit="candidates",
                status="healthy" if row_dict["candidates_in_pipeline"] > 0 else "warning"
            )),
        ("interviews_scheduled", lambda: KPIItem(
                key="interviews_scheduled",
                label="Interviews Scheduled",
                value=float(row_dict["interviews_scheduled"]),
                unit="interviews",
                status="neutral"
            )),
        ("offers_extended", lambda: KPIItem(
                key="offers_extended",
                label="Offers Extended",
                value=float(row_dict["offers_extended"]),
                unit="offers",
                status="neutral"
            )),
        ("offer_acceptance_pct", lambda: KPIItem(
                key="offer_acceptance_pct",
                label="Offer Acceptance %",
                value=float(row_dict["offer_acceptance_pct"]),
                unit="%",
                status="healthy" if row_dict["offer_acceptance_pct"] >= 80.0 else "warning"
            )),
        ("hires_this_month", lambda: KPIItem(
                key="hires_this_month",
                label="Hires This Month",
                value=float(row_dict["hires_this_month"]),
                unit="hires",
                status="neutral"
            )),
        ("average_time_to_fill", lambda: KPIItem(
                key="average_time_to_fill",
                label="Average Time to Fill",
                value=float(row_dict["average_time_to_fill"]),
                unit="days",
                status="warning" if row_dict["average_time_to_fill"] > 45 else "healthy"
            )),
        ("overdue_requisitions", lambda: KPIItem(
                key="overdue_requisitions",
                label="Overdue Requisitions",
                value=float(row_dict["overdue_requisitions"]),
                unit="requisitions",
                status="critical" if row_dict["overdue_requisitions"] > 0 else "healthy"
            )),
        ("workforce_plan_fulfillment_pct", lambda: KPIItem(
                key="workforce_plan_fulfillment_pct",
                label="Workforce Plan Fulfillment %",
                value=float(row_dict["workforce_plan_fulfillment_pct"]),
                unit="%",
                status="healthy" if row_dict["workforce_plan_fulfillment_pct"] >= 90.0 else "warning"
            )),
        ("recruitment_exception_count", lambda: KPIItem(
                key="recruitment_exception_count",
                label="Recruitment Exception Count",
                value=float(row_dict["recruitment_exception_count"]),
                unit="alerts",
                status="critical" if row_dict["recruitment_exception_count"] > 0 else "healthy"
            )),
    ])

    return RecruitmentSummaryResponse(report_month=report_month, kpis=kpis, suppressed=prov.block(),
        coverage_notes=prov.coverage_block())

@router.get("/pipeline", response_model=RecruitmentPipelineResponse)
@suppressible(RecruitmentPipelineResponse, "mart_recruitment_pipeline")
def get_recruitment_pipeline(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_pipeline").fetchall()
        pipeline = [PipelineStageItem(pipeline_stage=row[0] or "Applied", candidate_count=row[1]) for row in res]
        return RecruitmentPipelineResponse(pipeline=pipeline)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/trends", response_model=RecruitmentTrendsResponse)
@suppressible(RecruitmentTrendsResponse, "mart_recruitment_trends")
def get_recruitment_trends(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_trends ORDER BY period ASC").fetchall()
        trends = [RecruitmentTrendItem(period=row[0], requisitions_opened=row[1], hires=row[2]) for row in res]
        return RecruitmentTrendsResponse(trends=trends)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/by-project", response_model=RecruitmentByProjectResponse)
@suppressible(RecruitmentByProjectResponse, "mart_recruitment_by_project")
def get_recruitment_by_project(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_by_project").fetchall()
        projects = [
            RecruitmentByProjectItem(
                project=row[0] or "Unassigned",
                total_requisitions=row[1],
                open_requisitions=row[2],
                closed_requisitions=row[3],
                overdue_requisitions=row[4]
            ) for row in res
        ]
        return RecruitmentByProjectResponse(projects=projects)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/by-department", response_model=RecruitmentByDepartmentResponse)
@suppressible(RecruitmentByDepartmentResponse, "mart_recruitment_by_department")
def get_recruitment_by_department(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_by_department").fetchall()
        departments = [
            RecruitmentByDepartmentItem(
                department=row[0] or "Unassigned",
                total_requisitions=row[1],
                open_requisitions=row[2],
                closed_requisitions=row[3],
                overdue_requisitions=row[4]
            ) for row in res
        ]
        return RecruitmentByDepartmentResponse(departments=departments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/time-to-fill", response_model=TimeToFillResponse)
@suppressible(TimeToFillResponse, "mart_recruitment_time_to_fill")
def get_time_to_fill(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_time_to_fill").fetchall()
        ttf_mapped = []
        for row in res:
            ttf_mapped.append(TimeToFillItem(
                department=row[0] or "Unassigned",
                project=row[1] or "Unassigned",
                average_time_to_fill=float(row[2]),
                hire_count=int(row[3])
            ))
        return TimeToFillResponse(time_to_fill=ttf_mapped)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/source-effectiveness", response_model=SourceEffectivenessResponse)
@suppressible(SourceEffectivenessResponse, "mart_recruitment_source_effectiveness")
def get_source_effectiveness(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_source_effectiveness").fetchall()
        sources = [
            SourceEffectivenessItem(
                source=row[0] or "Other",
                candidate_count=row[1],
                hire_count=row[2],
                conversion_pct=row[3]
            ) for row in res
        ]
        return SourceEffectivenessResponse(sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/offers", response_model=OfferAcceptanceResponse)
@suppressible(OfferAcceptanceResponse, "mart_offer_acceptance")
def get_offer_acceptance(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_offer_acceptance").fetchall()
        offers = [OfferAcceptanceItem(offer_status=row[0] or "Pending", offer_count=row[1]) for row in res]
        return OfferAcceptanceResponse(offers=offers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/onboarding", response_model=OnboardingStatusResponse)
@suppressible(OnboardingStatusResponse, "mart_onboarding_status")
def get_onboarding_status(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_onboarding_status").fetchall()
        onboarding = [OnboardingStatusItem(onboarding_status=row[0] or "Unknown", hire_count=row[1]) for row in res]
        return OnboardingStatusResponse(onboarding=onboarding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/workforce-plan", response_model=WorkforcePlanVsActualResponse)
@suppressible(WorkforcePlanVsActualResponse, "mart_workforce_plan_vs_actual")
def get_workforce_plan_vs_actual(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_workforce_plan_vs_actual").fetchall()
        plan = [
            WorkforcePlanVsActualItem(
                project=row[0] or "Unassigned",
                department=row[1] or "Unassigned",
                planned_headcount=row[2],
                actual_headcount=row[3],
                fulfillment_pct=row[4]
            ) for row in res
        ]
        return WorkforcePlanVsActualResponse(plan=plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@router.get("/exceptions", response_model=RecruitmentExceptionsResponse)
@suppressible(RecruitmentExceptionsResponse, "mart_recruitment_exceptions")
def get_recruitment_exceptions(conn: duckdb.DuckDBPyConnection = Depends(get_db_connection), prov: Provenance = Depends(get_provenance)):
    try:

        res = conn.execute("SELECT * FROM mart_recruitment_exceptions").fetchall()
        exceptions = []
        for row in res:
            exceptions.append(DQExceptionItem(
                employee_id=row[0] or "N/A",
                employee_name="N/A",
                issue_type=row[1],
                description=row[2],
                severity=row[3],
                recommended_action=row[4]
            ))
        return RecruitmentExceptionsResponse(exceptions=exceptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
