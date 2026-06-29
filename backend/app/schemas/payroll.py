from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class PayrollReconciliationResponse(BaseModel):
    total_gross_payroll: float
    sum_displayed_components: float
    unreconciled_component_difference: float
    net_payroll: float
    gross_minus_deductions: float
    net_unreconciled_difference: float
    project_payroll_total: float
    department_payroll_total: float
    employees_paid_count: int
    payroll_exception_count: int

class PayrollSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]
    reconciliation: PayrollReconciliationResponse

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
    trends: List[PayrollTrendItem]

class PayrollByProjectItem(BaseModel):
    project: str
    headcount: int
    total_payroll_cost: float
    overtime_cost: float

class PayrollByProjectResponse(BaseModel):
    projects: List[PayrollByProjectItem]

class PayrollByDepartmentItem(BaseModel):
    department: str
    headcount: int
    total_payroll_cost: float
    overtime_cost: float

class PayrollByDepartmentResponse(BaseModel):
    departments: List[PayrollByDepartmentItem]

class PayrollComponentItem(BaseModel):
    component: str
    amount: float

class PayrollComponentsResponse(BaseModel):
    components: List[PayrollComponentItem]

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
    components: List[PayrollComponentVarianceItem]
    employees: List[PayrollEmployeeVarianceItem]

class PayrollExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
