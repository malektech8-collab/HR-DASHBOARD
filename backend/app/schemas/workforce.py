from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem

class WorkforceSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class WorkforceTrendsResponse(BaseModel):
    months: Optional[List[str]] = None
    # Ruling 2: a point before the declared history depth is null, so the chart
    # shows a gap rather than a derived-but-understated headcount.
    headcount_trend: Optional[List[Optional[int]]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class CategoryDistribution(BaseModel):
    labels: List[str]
    values: List[int]

class WorkforceDistributionResponse(BaseModel):
    # Five charts from ONE payload-mode mart, so they suppress together.
    # The mechanical sweep missed these because they are a nested BaseModel
    # rather than List[...] — see the step-2b report §3.
    department: Optional[CategoryDistribution] = None
    project: Optional[CategoryDistribution] = None
    nationality_group: Optional[CategoryDistribution] = None
    employment_type: Optional[CategoryDistribution] = None
    status: Optional[CategoryDistribution] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)


class ExpiryAgingResponse(BaseModel):
    expired: Optional[int] = None
    bucket_0_30: Optional[int] = Field(None, alias="0_30")
    bucket_31_60: Optional[int] = Field(None, alias="31_60")
    bucket_61_90: Optional[int] = Field(None, alias="61_90")
    bucket_90_plus: Optional[int] = Field(None, alias="90_plus")
    missing_date: Optional[int] = None

    model_config = {
        "populate_by_name": True
    }
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
