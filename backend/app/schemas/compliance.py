from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class ComplianceSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]

class SaudizationTrendItem(BaseModel):
    period: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    saudization_pct: float

class SaudizationSummaryResponse(BaseModel):
    trends: List[SaudizationTrendItem]

class SaudizationByProjectItem(BaseModel):
    project: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    total_headcount: int
    saudization_pct: float

class SaudizationByProjectResponse(BaseModel):
    projects: List[SaudizationByProjectItem]

class SaudizationByDepartmentItem(BaseModel):
    department: str
    saudi_headcount: int
    non_saudi_headcount: int
    employees_missing_nationality: int
    total_headcount: int
    saudization_pct: float

class SaudizationByDepartmentResponse(BaseModel):
    departments: List[SaudizationByDepartmentItem]

class DocumentExpiryItem(BaseModel):
    expiry_bucket: str
    iqama_count: int
    work_permit_count: int

class DocumentExpiryResponse(BaseModel):
    buckets: List[DocumentExpiryItem]

class GosiStatusItem(BaseModel):
    gosi_status: str
    employee_count: int

class GosiStatusResponse(BaseModel):
    statuses: List[GosiStatusItem]

class WpsStatusItem(BaseModel):
    wps_status: str
    headcount: int

class WpsStatusResponse(BaseModel):
    statuses: List[WpsStatusItem]

class ComplianceExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
