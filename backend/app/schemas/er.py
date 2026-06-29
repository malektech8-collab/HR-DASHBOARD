from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class ErSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]

class ErTrendItem(BaseModel):
    period: str
    new_cases: int
    closed_cases: int

class ErTrendResponse(BaseModel):
    trends: List[ErTrendItem]

class ErCasesByProjectItem(BaseModel):
    project: str
    total_cases: int
    open_cases: int
    closed_cases: int
    escalated_cases: int
    compliant_cases: int
    compliance_pct: float

class ErCasesByProjectResponse(BaseModel):
    projects: List[ErCasesByProjectItem]

class ErCasesByDepartmentItem(BaseModel):
    department: str
    total_cases: int
    open_cases: int
    closed_cases: int
    escalated_cases: int
    compliant_cases: int
    compliance_pct: float

class ErCasesByDepartmentResponse(BaseModel):
    departments: List[ErCasesByDepartmentItem]

class ErCaseTypeItem(BaseModel):
    case_type: str
    case_count: int

class ErCaseTypeResponse(BaseModel):
    case_types: List[ErCaseTypeItem]

class ErCaseStatusItem(BaseModel):
    case_status: str
    case_count: int

class ErCaseStatusResponse(BaseModel):
    statuses: List[ErCaseStatusItem]

class ErSlaPerformanceItem(BaseModel):
    category_type: str
    category: str
    eligible_count: int
    compliant_count: int
    breached_count: int
    compliance_pct: float

class ErSlaPerformanceResponse(BaseModel):
    performance: List[ErSlaPerformanceItem]

class ErAgingBucketItem(BaseModel):
    aging_bucket: str
    case_count: int

class ErAgingBucketResponse(BaseModel):
    buckets: List[ErAgingBucketItem]

class ErExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
