from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem

class ErSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErTrendItem(BaseModel):
    period: str
    new_cases: int
    closed_cases: int

class ErTrendResponse(BaseModel):
    trends: Optional[List[ErTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErCasesByProjectItem(BaseModel):
    project: str
    total_cases: int
    open_cases: int
    closed_cases: int
    escalated_cases: int
    compliant_cases: int
    compliance_pct: float

class ErCasesByProjectResponse(BaseModel):
    projects: Optional[List[ErCasesByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErCasesByDepartmentItem(BaseModel):
    department: str
    total_cases: int
    open_cases: int
    closed_cases: int
    escalated_cases: int
    compliant_cases: int
    compliance_pct: float

class ErCasesByDepartmentResponse(BaseModel):
    departments: Optional[List[ErCasesByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErCaseTypeItem(BaseModel):
    case_type: str
    case_count: int

class ErCaseTypeResponse(BaseModel):
    case_types: Optional[List[ErCaseTypeItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErCaseStatusItem(BaseModel):
    case_status: str
    case_count: int

class ErCaseStatusResponse(BaseModel):
    statuses: Optional[List[ErCaseStatusItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErSlaPerformanceItem(BaseModel):
    category_type: str
    category: str
    eligible_count: int
    compliant_count: int
    breached_count: int
    compliance_pct: float

class ErSlaPerformanceResponse(BaseModel):
    performance: Optional[List[ErSlaPerformanceItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErAgingBucketItem(BaseModel):
    aging_bucket: str
    case_count: int

class ErAgingBucketResponse(BaseModel):
    buckets: Optional[List[ErAgingBucketItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ErExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
