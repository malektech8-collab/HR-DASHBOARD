from fastapi import APIRouter, HTTPException
from app.db.duckdb_client import DuckDBClient
from app.schemas.talent import (
    TalentSummaryResponse,
    PerformanceDistributionResponse,
    PerformanceDistributionItem,
    PerformanceTrendsResponse,
    PerformanceTrendItem,
    PerformanceByProjectResponse,
    PerformanceByProjectItem,
    PerformanceByDepartmentResponse,
    PerformanceByDepartmentItem,
    GoalCompletionResponse,
    GoalCompletionItem,
    CompetencyGapResponse,
    CompetencyGapItem,
    LearningCompletionResponse,
    LearningCompletionItem,
    LearningByProjectResponse,
    LearningByProjectItem,
    SuccessionCoverageResponse,
    SuccessionCoverageItem,
    SuccessorReadinessResponse,
    SuccessorReadinessItem,
    TalentRiskResponse,
    TalentRiskItem,
    TalentExceptionsResponse,
)
from app.schemas.kpi import KPIItem, DQExceptionItem
import os
import yaml

router = APIRouter()


def get_talent_report_month():
    """Resolve the talent report month using the 5-tier priority."""
    try:
        config_path = "config/business_rules.yml"
        rules = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f) or {}
        talent_rules = rules.get("talent_rules", {})
        configured = talent_rules.get("configured_report_month", None)
        if configured:
            return configured

        conn = DuckDBClient.get_connection()
        try:
            row = conn.execute(
                "SELECT MAX(review_period) FROM performance_reviews WHERE review_period IS NOT NULL"
            ).fetchone()
            if row and row[0]:
                return str(row[0])[:7]
        except Exception:
            pass
        try:
            row = conn.execute(
                "SELECT MAX(completion_date) FROM learning_enrollments WHERE completion_date IS NOT NULL"
            ).fetchone()
            if row and row[0]:
                return str(row[0])[:7]
        except Exception:
            pass
        finally:
            conn.close()
    except Exception:
        pass
    return "2026-06"


@router.get("/summary", response_model=TalentSummaryResponse)
def get_talent_summary():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_talent_kpis").fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="No talent KPI records found")
        cols = [desc[0] for desc in conn.description]
        row_dict = dict(zip(cols, res))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()

    report_month = get_talent_report_month()

    kpis = [
        KPIItem(
            key="employees_reviewed",
            label="Employees Reviewed",
            value=float(row_dict["employees_reviewed"]),
            unit="employees",
            status="healthy" if row_dict["employees_reviewed"] > 0 else "warning",
        ),
        KPIItem(
            key="review_completion_pct",
            label="Review Completion %",
            value=float(row_dict["review_completion_pct"]),
            unit="%",
            status="healthy" if row_dict["review_completion_pct"] >= 80.0 else "warning",
        ),
        KPIItem(
            key="average_performance_rating",
            label="Average Performance Rating",
            value=float(row_dict["average_performance_rating"] or 0.0),
            unit="rating",
            status="healthy" if (row_dict["average_performance_rating"] or 0) >= 3.5 else "warning",
        ),
        KPIItem(
            key="high_performers",
            label="High Performers",
            value=float(row_dict["high_performers"]),
            unit="employees",
            status="healthy",
        ),
        KPIItem(
            key="low_performers",
            label="Low / At-Risk Performers",
            value=float(row_dict["low_performers"]),
            unit="employees",
            status="critical" if row_dict["low_performers"] > 0 else "healthy",
        ),
        KPIItem(
            key="goal_completion_pct",
            label="Goal Completion %",
            value=float(row_dict["goal_completion_pct"]),
            unit="%",
            status="healthy" if row_dict["goal_completion_pct"] >= 75.0 else "warning",
        ),
        KPIItem(
            key="training_completion_pct",
            label="Training Completion %",
            value=float(row_dict["training_completion_pct"]),
            unit="%",
            status="healthy" if row_dict["training_completion_pct"] >= 70.0 else "warning",
        ),
        KPIItem(
            key="average_training_hours",
            label="Avg Training Hours / Employee",
            value=float(row_dict["average_training_hours"]),
            unit="hours",
            status="neutral",
        ),
        KPIItem(
            key="critical_roles_covered_pct",
            label="Critical Roles Covered %",
            value=float(row_dict["critical_roles_covered_pct"]),
            unit="%",
            status="healthy" if row_dict["critical_roles_covered_pct"] >= 80.0 else "critical",
        ),
        KPIItem(
            key="ready_successors",
            label="Ready Now Successors",
            value=float(row_dict["ready_successors"]),
            unit="employees",
            status="healthy" if row_dict["ready_successors"] > 0 else "warning",
        ),
        KPIItem(
            key="talent_exception_count",
            label="Talent Data Exceptions",
            value=float(row_dict["talent_exception_count"]),
            unit="alerts",
            status="critical" if row_dict["talent_exception_count"] > 0 else "healthy",
        ),
    ]

    return TalentSummaryResponse(report_month=report_month, kpis=kpis)


@router.get("/performance-distribution", response_model=PerformanceDistributionResponse)
def get_performance_distribution():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_performance_distribution ORDER BY performance_category").fetchall()
        distribution = [
            PerformanceDistributionItem(
                performance_category=row[0] or "Unknown",
                employee_count=int(row[1]),
            )
            for row in res
        ]
        return PerformanceDistributionResponse(distribution=distribution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/trends", response_model=PerformanceTrendsResponse)
def get_performance_trends():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute(
            "SELECT * FROM mart_talent_review_trends ORDER BY period ASC"
        ).fetchall()
        trends = [
            PerformanceTrendItem(
                period=row[0],
                total_reviewed=int(row[1]),
                completed_reviews=int(row[2]),
                completion_pct=float(row[3] or 0.0),
                avg_rating=float(row[4] or 0.0),
            )
            for row in res
        ]
        return PerformanceTrendsResponse(trends=trends)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/by-project", response_model=PerformanceByProjectResponse)
def get_performance_by_project():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_performance_by_project ORDER BY project").fetchall()
        projects = [
            PerformanceByProjectItem(
                project=row[0] or "Unassigned",
                reviewed_count=int(row[1]),
                average_rating=float(row[2] or 0.0),
                high_performers=int(row[3]),
                low_performers=int(row[4]),
            )
            for row in res
        ]
        return PerformanceByProjectResponse(projects=projects)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/by-department", response_model=PerformanceByDepartmentResponse)
def get_performance_by_department():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_performance_by_department ORDER BY department").fetchall()
        departments = [
            PerformanceByDepartmentItem(
                department=row[0] or "Unknown",
                reviewed_count=int(row[1]),
                average_rating=float(row[2] or 0.0),
                high_performers=int(row[3]),
                low_performers=int(row[4]),
            )
            for row in res
        ]
        return PerformanceByDepartmentResponse(departments=departments)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/goals", response_model=GoalCompletionResponse)
def get_goal_completion():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_goal_completion ORDER BY department").fetchall()
        goals = [
            GoalCompletionItem(
                department=row[0] or "Unknown",
                completed_goals=int(row[1]),
                in_progress_goals=int(row[2]),
                overdue_goals=int(row[3]),
                not_started_goals=int(row[4]),
                cancelled_goals=int(row[5]),
                eligible_goals=int(row[6]),
            )
            for row in res
        ]
        return GoalCompletionResponse(goals=goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/competency-gaps", response_model=CompetencyGapResponse)
def get_competency_gaps():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_competency_gaps ORDER BY avg_gap DESC").fetchall()
        gaps = [
            CompetencyGapItem(
                competency_name=row[0] or "Unknown",
                avg_required=float(row[1] or 0.0),
                avg_actual=float(row[2] or 0.0),
                avg_gap=float(row[3] or 0.0),
            )
            for row in res
        ]
        return CompetencyGapResponse(gaps=gaps)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/learning", response_model=LearningCompletionResponse)
def get_learning_completion():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_learning_completion ORDER BY category").fetchall()
        completion = [
            LearningCompletionItem(
                category=row[0] or "Uncategorized",
                completed_enrollments=int(row[1]),
                eligible_enrollments=int(row[2]),
                total_hours=float(row[3] or 0.0),
            )
            for row in res
        ]
        return LearningCompletionResponse(completion=completion)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/learning-by-project", response_model=LearningByProjectResponse)
def get_learning_by_project():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_learning_by_project ORDER BY project, department").fetchall()
        projects = [
            LearningByProjectItem(
                project=row[0] or "Unassigned",
                department=row[1] or "Unknown",
                completed_enrollments=int(row[2]),
                total_hours=float(row[3] or 0.0),
            )
            for row in res
        ]
        return LearningByProjectResponse(projects=projects)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/succession", response_model=SuccessionCoverageResponse)
def get_succession_coverage():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_succession_coverage ORDER BY role_title").fetchall()
        coverage = [
            SuccessionCoverageItem(
                critical_role_id=row[0] or "N/A",
                role_title=row[1] or "Unknown",
                valid_successor_count=int(row[2]),
                coverage_status=row[3] or "Not Covered",
            )
            for row in res
        ]
        return SuccessionCoverageResponse(coverage=coverage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/succession-readiness", response_model=SuccessorReadinessResponse)
def get_successor_readiness():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_successor_readiness ORDER BY readiness").fetchall()
        readiness = [
            SuccessorReadinessItem(
                readiness=row[0] or "Missing",
                successor_count=int(row[1]),
            )
            for row in res
        ]
        return SuccessorReadinessResponse(readiness=readiness)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/risk", response_model=TalentRiskResponse)
def get_talent_risk():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute("SELECT * FROM mart_talent_risk ORDER BY risk_category, department").fetchall()
        risks = [
            TalentRiskItem(
                employee_id=row[0] or "N/A",
                department=row[1] or "Unknown",
                project=row[2] or "Unassigned",
                performance_category=row[3],
                potential_rating=row[4] or "Unknown",
                flight_risk=row[5] or "Unknown",
                risk_category=row[6] or "Low Risk",
            )
            for row in res
        ]
        return TalentRiskResponse(risks=risks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/exceptions", response_model=TalentExceptionsResponse)
def get_talent_exceptions():
    conn = None
    try:
        conn = DuckDBClient.get_connection()
        res = conn.execute(
            "SELECT record_id_str, issue_type, description, severity, recommended_action FROM mart_talent_exceptions ORDER BY severity DESC, issue_type"
        ).fetchall()
        exceptions = [
            DQExceptionItem(
                employee_id=row[0] or "N/A",
                employee_name="N/A",
                issue_type=row[1],
                description=row[2],
                severity=row[3],
                recommended_action=row[4],
            )
            for row in res
        ]
        return TalentExceptionsResponse(exceptions=exceptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        if conn:
            conn.close()
