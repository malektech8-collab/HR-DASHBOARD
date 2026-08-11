from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem

class RecruitmentSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class PipelineStageItem(BaseModel):
    pipeline_stage: str
    candidate_count: int

class RecruitmentPipelineResponse(BaseModel):
    pipeline: Optional[List[PipelineStageItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class RecruitmentTrendItem(BaseModel):
    period: str
    requisitions_opened: int
    hires: int

class RecruitmentTrendsResponse(BaseModel):
    trends: Optional[List[RecruitmentTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class RecruitmentByProjectItem(BaseModel):
    project: str
    total_requisitions: int
    open_requisitions: int
    closed_requisitions: int
    overdue_requisitions: int

class RecruitmentByProjectResponse(BaseModel):
    projects: Optional[List[RecruitmentByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class RecruitmentByDepartmentItem(BaseModel):
    department: str
    total_requisitions: int
    open_requisitions: int
    closed_requisitions: int
    overdue_requisitions: int

class RecruitmentByDepartmentResponse(BaseModel):
    departments: Optional[List[RecruitmentByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class TimeToFillItem(BaseModel):
    department: str
    project: str
    average_time_to_fill: float
    hire_count: int

class TimeToFillResponse(BaseModel):
    time_to_fill: Optional[List[TimeToFillItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class SourceEffectivenessItem(BaseModel):
    source: str
    candidate_count: int
    hire_count: int
    conversion_pct: float

class SourceEffectivenessResponse(BaseModel):
    sources: Optional[List[SourceEffectivenessItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class OfferAcceptanceItem(BaseModel):
    offer_status: str
    offer_count: int

class OfferAcceptanceResponse(BaseModel):
    offers: Optional[List[OfferAcceptanceItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class OnboardingStatusItem(BaseModel):
    onboarding_status: str
    hire_count: int

class OnboardingStatusResponse(BaseModel):
    onboarding: Optional[List[OnboardingStatusItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class WorkforcePlanVsActualItem(BaseModel):
    project: str
    department: str
    planned_headcount: int
    actual_headcount: int
    fulfillment_pct: float

class WorkforcePlanVsActualResponse(BaseModel):
    plan: Optional[List[WorkforcePlanVsActualItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class RecruitmentExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
