from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class WorkforceSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]

class WorkforceTrendsResponse(BaseModel):
    months: List[str]
    headcount_trend: List[int]

class CategoryDistribution(BaseModel):
    labels: List[str]
    values: List[int]

class WorkforceDistributionResponse(BaseModel):
    department: CategoryDistribution
    project: CategoryDistribution
    nationality_group: CategoryDistribution
    employment_type: CategoryDistribution
    status: CategoryDistribution

class ExpiryAgingResponse(BaseModel):
    expired: int
    bucket_0_30: int = Field(..., alias="0_30")
    bucket_31_60: int = Field(..., alias="31_60")
    bucket_61_90: int = Field(..., alias="61_90")
    bucket_90_plus: int = Field(..., alias="90_plus")
    missing_date: int

    model_config = {
        "populate_by_name": True
    }
