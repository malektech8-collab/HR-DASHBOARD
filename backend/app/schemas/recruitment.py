from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class RecruitmentSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]

class PipelineStageItem(BaseModel):
    pipeline_stage: str
    candidate_count: int

class RecruitmentPipelineResponse(BaseModel):
    pipeline: List[PipelineStageItem]

class RecruitmentTrendItem(BaseModel):
    period: str
    requisitions_opened: int
    hires: int

class RecruitmentTrendsResponse(BaseModel):
    trends: List[RecruitmentTrendItem]

class RecruitmentByProjectItem(BaseModel):
    project: str
    total_requisitions: int
    open_requisitions: int
    closed_requisitions: int
    overdue_requisitions: int

class RecruitmentByProjectResponse(BaseModel):
    projects: List[RecruitmentByProjectItem]

class RecruitmentByDepartmentItem(BaseModel):
    department: str
    total_requisitions: int
    open_requisitions: int
    closed_requisitions: int
    overdue_requisitions: int

class RecruitmentByDepartmentResponse(BaseModel):
    departments: List[RecruitmentByDepartmentItem]

class TimeToFillItem(BaseModel):
    department: str
    project: str
    average_time_to_fill: float
    hire_count: int

class TimeToFillResponse(BaseModel):
    time_to_fill: List[TimeToFillItem]

class SourceEffectivenessItem(BaseModel):
    source: str
    candidate_count: int
    hire_count: int
    conversion_pct: float

class SourceEffectivenessResponse(BaseModel):
    sources: List[SourceEffectivenessItem]

class OfferAcceptanceItem(BaseModel):
    offer_status: str
    offer_count: int

class OfferAcceptanceResponse(BaseModel):
    offers: List[OfferAcceptanceItem]

class OnboardingStatusItem(BaseModel):
    onboarding_status: str
    hire_count: int

class OnboardingStatusResponse(BaseModel):
    onboarding: List[OnboardingStatusItem]

class WorkforcePlanVsActualItem(BaseModel):
    project: str
    department: str
    planned_headcount: int
    actual_headcount: int
    fulfillment_pct: float

class WorkforcePlanVsActualResponse(BaseModel):
    plan: List[WorkforcePlanVsActualItem]

class RecruitmentExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
