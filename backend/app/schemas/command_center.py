from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.kpi import KPIItem, SuppressionItem

class CommandCenterOverviewResponse(BaseModel):
    active_headcount: Optional[int] = None
    payroll_cost: Optional[float] = None
    attendance_compliance_pct: Optional[float] = None
    saudization_pct: Optional[float] = None
    open_er_cases: Optional[int] = None
    open_requisitions: Optional[int] = None
    review_completion_pct: Optional[float] = None
    total_active_exceptions: Optional[int] = None
    modules_healthy: Optional[int] = None
    last_data_refresh: datetime
    latest_source_business_date: Optional[str]
    data_quality_score: Optional[float] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ModuleHealthItem(BaseModel):
    module_key: str
    module_label: str
    route_path: str
    owner_domain: str
    api_health_status: str
    reconciliation_status: str
    required_marts_present: bool
    stale_flag: bool
    critical_exception_count: int
    warning_exception_count: int
    status: str
    primary_kpi_count: int
    screenshot_path: Optional[str]
    qa_report_path: Optional[str]

class ModuleHealthResponse(BaseModel):
    modules: Optional[List[ModuleHealthItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class PriorityAlertItem(BaseModel):
    alert_id: str
    module_key: str
    module_label: str
    severity: str
    issue_type: str
    issue_count: int
    recommended_action: Optional[str]
    source_mart: str
    route_path: str

class PriorityAlertResponse(BaseModel):
    alerts: Optional[List[PriorityAlertItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ExceptionSummaryItem(BaseModel):
    module_key: str
    module_label: str
    severity: str
    issue_type: str
    exception_count: int
    recommended_action: Optional[str]
    route_path: str

class ExceptionSummaryResponse(BaseModel):
    exceptions: Optional[List[ExceptionSummaryItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class FreshnessItem(BaseModel):
    module_key: str
    module_label: str
    source_table: str
    max_source_date: Optional[str]
    last_refresh_timestamp: datetime
    stale_flag: bool
    stale_reason: str

class FreshnessResponse(BaseModel):
    freshness: Optional[List[FreshnessItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class NavigationStatusItem(BaseModel):
    module_key: str
    page_key: str
    route_path: str
    status: str

class NavigationStatusResponse(BaseModel):
    navigation: Optional[List[NavigationStatusItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class FilterOptionsResponse(BaseModel):
    report_month: str
    companies: Optional[List[str]] = None
    projects: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    cost_centers: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    nationalities: Optional[List[str]] = None
    modules: Optional[List[str]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class QaIndexItem(BaseModel):
    module_key: str
    module_label: str
    screenshot_path: str
    screenshot_exists: bool
    qa_report_path: str
    qa_report_exists: bool
    raw_api_path: str
    raw_api_exists: bool
    status: str

class QaIndexResponse(BaseModel):
    qa_index: Optional[List[QaIndexItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
