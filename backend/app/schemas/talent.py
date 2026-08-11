from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem, CoverageItem


class TalentSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PerformanceDistributionItem(BaseModel):
    performance_category: str
    employee_count: int


class PerformanceDistributionResponse(BaseModel):
    distribution: Optional[List[PerformanceDistributionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PerformanceTrendItem(BaseModel):
    period: str
    total_reviewed: int
    completed_reviews: int
    completion_pct: float
    avg_rating: float


class PerformanceTrendsResponse(BaseModel):
    trends: Optional[List[PerformanceTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PerformanceByProjectItem(BaseModel):
    project: str
    reviewed_count: int
    average_rating: float
    high_performers: int
    low_performers: int


class PerformanceByProjectResponse(BaseModel):
    projects: Optional[List[PerformanceByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PerformanceByDepartmentItem(BaseModel):
    department: str
    reviewed_count: int
    average_rating: float
    high_performers: int
    low_performers: int


class PerformanceByDepartmentResponse(BaseModel):
    departments: Optional[List[PerformanceByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class GoalCompletionItem(BaseModel):
    department: str
    completed_goals: int
    in_progress_goals: int
    overdue_goals: int
    not_started_goals: int
    cancelled_goals: int
    eligible_goals: int


class GoalCompletionResponse(BaseModel):
    goals: Optional[List[GoalCompletionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class CompetencyGapItem(BaseModel):
    competency_name: str
    avg_required: float
    avg_actual: float
    avg_gap: float


class CompetencyGapResponse(BaseModel):
    gaps: Optional[List[CompetencyGapItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class LearningCompletionItem(BaseModel):
    category: str
    completed_enrollments: int
    eligible_enrollments: int
    total_hours: float


class LearningCompletionResponse(BaseModel):
    completion: Optional[List[LearningCompletionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class LearningByProjectItem(BaseModel):
    project: str
    department: str
    completed_enrollments: int
    total_hours: float


class LearningByProjectResponse(BaseModel):
    projects: Optional[List[LearningByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class SuccessionCoverageItem(BaseModel):
    critical_role_id: str
    role_title: str
    valid_successor_count: int
    coverage_status: str


class SuccessionCoverageResponse(BaseModel):
    coverage: Optional[List[SuccessionCoverageItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class SuccessorReadinessItem(BaseModel):
    readiness: str
    successor_count: int


class SuccessorReadinessResponse(BaseModel):
    readiness: Optional[List[SuccessorReadinessItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class TalentRiskItem(BaseModel):
    employee_id: str
    department: str
    project: str
    performance_category: Optional[str]
    potential_rating: str
    flight_risk: str
    risk_category: str


class TalentRiskResponse(BaseModel):
    risks: Optional[List[TalentRiskItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class TalentExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)
