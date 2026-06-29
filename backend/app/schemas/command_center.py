from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.kpi import KPIItem

class CommandCenterOverviewResponse(BaseModel):
    active_headcount: int
    payroll_cost: float
    attendance_compliance_pct: float
    saudization_pct: float
    open_er_cases: int
    open_requisitions: int
    review_completion_pct: float
    total_active_exceptions: int
    modules_healthy: int
    last_data_refresh: datetime
    latest_source_business_date: Optional[str]
    data_quality_score: float

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
    modules: List[ModuleHealthItem]

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
    alerts: List[PriorityAlertItem]

class ExceptionSummaryItem(BaseModel):
    module_key: str
    module_label: str
    severity: str
    issue_type: str
    exception_count: int
    recommended_action: Optional[str]
    route_path: str

class ExceptionSummaryResponse(BaseModel):
    exceptions: List[ExceptionSummaryItem]

class FreshnessItem(BaseModel):
    module_key: str
    module_label: str
    source_table: str
    max_source_date: Optional[str]
    last_refresh_timestamp: datetime
    stale_flag: bool
    stale_reason: str

class FreshnessResponse(BaseModel):
    freshness: List[FreshnessItem]

class NavigationStatusItem(BaseModel):
    module_key: str
    page_key: str
    route_path: str
    status: str

class NavigationStatusResponse(BaseModel):
    navigation: List[NavigationStatusItem]

class FilterOptionsResponse(BaseModel):
    report_month: str
    companies: List[str]
    projects: List[str]
    departments: List[str]
    cost_centers: List[str]
    locations: List[str]
    nationalities: List[str]
    modules: List[str]

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
    qa_index: List[QaIndexItem]
