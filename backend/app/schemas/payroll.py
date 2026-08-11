from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem, CoverageItem

class PayrollReconciliationResponse(BaseModel):
    total_gross_payroll: Optional[float] = None
    sum_displayed_components: Optional[float] = None
    unreconciled_component_difference: Optional[float] = None
    net_payroll: Optional[float] = None
    gross_minus_deductions: Optional[float] = None
    net_unreconciled_difference: Optional[float] = None
    project_payroll_total: Optional[float] = None
    department_payroll_total: Optional[float] = None
    employees_paid_count: Optional[int] = None
    payroll_exception_count: Optional[int] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    reconciliation: Optional[PayrollReconciliationResponse] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollTrendItem(BaseModel):
    month: str
    total_payroll_cost: float
    basic_salary: float
    allowances: float
    overtime: float
    deductions: float
    net_payroll: float
    headcount: int

class PayrollTrendsResponse(BaseModel):
    trends: Optional[List[PayrollTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollByProjectItem(BaseModel):
    project: str
    headcount: int
    total_payroll_cost: float
    overtime_cost: float

class PayrollByProjectResponse(BaseModel):
    projects: Optional[List[PayrollByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollByDepartmentItem(BaseModel):
    department: str
    headcount: int
    total_payroll_cost: float
    overtime_cost: float

class PayrollByDepartmentResponse(BaseModel):
    departments: Optional[List[PayrollByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollComponentItem(BaseModel):
    component: str
    amount: float

class PayrollComponentsResponse(BaseModel):
    components: Optional[List[PayrollComponentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollComponentVarianceItem(BaseModel):
    component: str
    prev_amount: float
    curr_amount: float
    change_amount: float
    change_pct: float

class PayrollEmployeeVarianceItem(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    prev_amount: float
    curr_amount: float
    change_amount: float
    change_pct: float

class PayrollVarianceResponse(BaseModel):
    components: Optional[List[PayrollComponentVarianceItem]] = None
    employees: Optional[List[PayrollEmployeeVarianceItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class PayrollExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)
