from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class KPIItem(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    trend_value: Optional[float] = None
    trend_direction: Optional[str] = None  # "up", "down", "flat"
    status: str  # "healthy", "warning", "critical", "neutral"

class ExecutiveSummaryResponse(BaseModel):
    report_month: str
    last_refresh_at: str
    kpis: List[KPIItem]
    charts: Dict[str, Any]

class DataQualitySummaryResponse(BaseModel):
    data_quality_score: float
    missing_manager_count: int
    missing_project_count: int
    missing_cost_center_count: int
    missing_nationality_count: int
    duplicate_employee_count: int
    invalid_payroll_count: int

class DQExceptionItem(BaseModel):
    employee_id: str
    employee_name: str
    issue_type: str
    description: str
    severity: str
    recommended_action: str

class DQExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]

class RefreshStatusResponse(BaseModel):
    last_refresh_at: str
    status: str
