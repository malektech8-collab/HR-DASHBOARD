from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem, CoverageItem

class ComplianceSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class SaudizationTrendItem(BaseModel):
    period: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    saudization_pct: float

class SaudizationSummaryResponse(BaseModel):
    trends: Optional[List[SaudizationTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class SaudizationByProjectItem(BaseModel):
    project: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    total_headcount: int
    saudization_pct: float

class SaudizationByProjectResponse(BaseModel):
    projects: Optional[List[SaudizationByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class SaudizationByDepartmentItem(BaseModel):
    department: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    total_headcount: int
    saudization_pct: float

class SaudizationByDepartmentResponse(BaseModel):
    departments: Optional[List[SaudizationByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class DocumentExpiryItem(BaseModel):
    expiry_bucket: str
    iqama_count: int
    work_permit_count: int

class DocumentExpiryResponse(BaseModel):
    buckets: Optional[List[DocumentExpiryItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class GosiStatusItem(BaseModel):
    gosi_status: str
    employee_count: int

class GosiStatusResponse(BaseModel):
    statuses: Optional[List[GosiStatusItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class WpsStatusItem(BaseModel):
    wps_status: str
    headcount: int

class WpsStatusResponse(BaseModel):
    statuses: Optional[List[WpsStatusItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class ComplianceExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)
