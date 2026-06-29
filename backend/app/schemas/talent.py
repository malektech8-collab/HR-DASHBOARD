from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem


class TalentSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]


class PerformanceDistributionItem(BaseModel):
    performance_category: str
    employee_count: int


class PerformanceDistributionResponse(BaseModel):
    distribution: List[PerformanceDistributionItem]


class PerformanceTrendItem(BaseModel):
    period: str
    total_reviewed: int
    completed_reviews: int
    completion_pct: float
    avg_rating: float


class PerformanceTrendsResponse(BaseModel):
    trends: List[PerformanceTrendItem]


class PerformanceByProjectItem(BaseModel):
    project: str
    reviewed_count: int
    average_rating: float
    high_performers: int
    low_performers: int


class PerformanceByProjectResponse(BaseModel):
    projects: List[PerformanceByProjectItem]


class PerformanceByDepartmentItem(BaseModel):
    department: str
    reviewed_count: int
    average_rating: float
    high_performers: int
    low_performers: int


class PerformanceByDepartmentResponse(BaseModel):
    departments: List[PerformanceByDepartmentItem]


class GoalCompletionItem(BaseModel):
    department: str
    completed_goals: int
    in_progress_goals: int
    overdue_goals: int
    not_started_goals: int
    cancelled_goals: int
    eligible_goals: int


class GoalCompletionResponse(BaseModel):
    goals: List[GoalCompletionItem]


class CompetencyGapItem(BaseModel):
    competency_name: str
    avg_required: float
    avg_actual: float
    avg_gap: float


class CompetencyGapResponse(BaseModel):
    gaps: List[CompetencyGapItem]


class LearningCompletionItem(BaseModel):
    category: str
    completed_enrollments: int
    eligible_enrollments: int
    total_hours: float


class LearningCompletionResponse(BaseModel):
    completion: List[LearningCompletionItem]


class LearningByProjectItem(BaseModel):
    project: str
    department: str
    completed_enrollments: int
    total_hours: float


class LearningByProjectResponse(BaseModel):
    projects: List[LearningByProjectItem]


class SuccessionCoverageItem(BaseModel):
    critical_role_id: str
    role_title: str
    valid_successor_count: int
    coverage_status: str


class SuccessionCoverageResponse(BaseModel):
    coverage: List[SuccessionCoverageItem]


class SuccessorReadinessItem(BaseModel):
    readiness: str
    successor_count: int


class SuccessorReadinessResponse(BaseModel):
    readiness: List[SuccessorReadinessItem]


class TalentRiskItem(BaseModel):
    employee_id: str
    department: str
    project: str
    performance_category: Optional[str]
    potential_rating: str
    flight_risk: str
    risk_category: str


class TalentRiskResponse(BaseModel):
    risks: List[TalentRiskItem]


class TalentExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
