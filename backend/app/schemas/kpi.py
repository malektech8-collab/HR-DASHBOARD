from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SuppressionItem(BaseModel):
    """One figure withheld because its source domain was not provided.

    Step 2b. Every response carries a `suppressed` list of these, so a missing
    number is never merely missing: it is named, attributed to the domains that
    would make it real, and explained in both languages.

    A null value with no entry here would be indistinguishable from a bug, and
    a client who cannot tell those apart will assume the number is a bug and
    ask for it to be "fixed" - which is how a fabricated number gets restored.
    """
    key: str                        # response field or metric key
    mart: str                       # the mart that would have supplied it
    missing_domains: List[str]      # what the client still has to provide
    reason: str                     # "not_provided" | "not_mapped"
    message_en: str
    message_ar: str

class CoverageItem(BaseModel):
    """A figure that is PRESENT but measured over less than the whole period.

    Deliberately NOT a fourth `suppressed` reason code. `suppressed` means
    withheld, and it carries every P0 guarantee step 2b established: if it ever
    also meant "shown but qualified", a reader could no longer infer absence
    from a suppression, and the damage would stay invisible until somebody
    trusted the wrong number.

    `covered_days` counts WORKING DAYS INSIDE THE DECLARED WINDOW, not days
    that happen to carry rows. A day inside the window with no row is a real
    absence - that is Category F's inversion - so counting rows would
    double-count what that design separated.
    """
    domain: str
    domain_label_en: str
    domain_label_ar: str
    declared_start: Optional[str] = None
    declared_end: Optional[str] = None
    covered_days: int
    expected_days: int
    coverage_pct: float
    message_en: str
    message_ar: str


class KPIItem(BaseModel):
    key: str
    label: str
    # Category F: null when the metric is genuinely UNMEASURABLE - the domain
    # was provided, but not for the days it would need. Distinct from a
    # suppressed card, which is absent from the list and named in `suppressed`.
    value: Optional[float] = None
    unit: str
    trend_value: Optional[float] = None
    trend_direction: Optional[str] = None  # "up", "down", "flat"
    status: str  # "healthy", "warning", "critical", "neutral"

class ExecutiveSummaryResponse(BaseModel):
    report_month: str
    last_refresh_at: str
    kpis: Optional[List[KPIItem]] = None
    charts: Optional[Dict[str, Any]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class DataQualitySummaryResponse(BaseModel):
    data_quality_score: Optional[float] = None
    missing_manager_count: Optional[int] = None
    missing_project_count: Optional[int] = None
    missing_cost_center_count: Optional[int] = None
    missing_nationality_count: Optional[int] = None
    duplicate_employee_count: Optional[int] = None
    invalid_payroll_count: Optional[int] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class DQExceptionItem(BaseModel):
    employee_id: str
    employee_name: str
    issue_type: str
    description: str
    severity: str
    recommended_action: str

class DQExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class RefreshStatusResponse(BaseModel):
    last_refresh_at: str
    status: str

class AppConfigResponse(BaseModel):
    data_mode: str
