from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem, SuppressionItem, CoverageItem

class AttendanceSummaryResponse(BaseModel):
    report_month: str
    kpis: Optional[List[KPIItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceTrendItem(BaseModel):
    month: str
    attendance_compliance_pct: float
    absence_days: float
    late_minutes: float
    net_late_minutes: float
    missing_punch_count: float
    overtime_hours: float

class AttendanceTrendsResponse(BaseModel):
    trends: Optional[List[AttendanceTrendItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceByProjectItem(BaseModel):
    project: str
    headcount: int
    # Category F: null when no day in this group was reported on.
    attendance_compliance_pct: Optional[float] = None
    absence_days: Optional[float] = None
    late_minutes: float
    missing_punches: int
    overtime_hours: float
    overtime_cost: float

class AttendanceByProjectResponse(BaseModel):
    projects: Optional[List[AttendanceByProjectItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceByDepartmentItem(BaseModel):
    department: str
    headcount: int
    # Category F: null when no day in this group was reported on.
    attendance_compliance_pct: Optional[float] = None
    absence_days: Optional[float] = None
    late_minutes: float
    net_late_minutes: float
    missing_punches: int
    overtime_hours: float
    overtime_cost: float

class AttendanceByDepartmentResponse(BaseModel):
    departments: Optional[List[AttendanceByDepartmentItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceLateArrivalItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str] = None
    project: Optional[str] = None
    total_late_minutes: int
    total_excused_minutes: int
    total_net_late_minutes: int
    late_arrival_incidents_count: int

class AttendanceLateArrivalResponse(BaseModel):
    late_arrivals: Optional[List[AttendanceLateArrivalItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceOvertimeItem(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    project: Optional[str] = None
    attendance_ot_hours: float
    payroll_ot_cost: float
    reconciliation_status: str

class AttendanceOvertimeResponse(BaseModel):
    overtime_records: Optional[List[AttendanceOvertimeItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceMissingPunchesItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str] = None
    project: Optional[str] = None
    missing_check_in_count: int
    missing_check_out_count: int
    total_missing_punches: int

class AttendanceMissingPunchesResponse(BaseModel):
    missing_punches: Optional[List[AttendanceMissingPunchesItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)


class AttendanceExceptionsResponse(BaseModel):
    exceptions: Optional[List[DQExceptionItem]] = None
    # Withheld figures, named. Empty when nothing was suppressed.
    suppressed: List[SuppressionItem] = Field(default_factory=list)
    # Present, but measured over less than the whole period. A SIBLING
    # of `suppressed`, never a reason code inside it - see CoverageItem.
    coverage_notes: List[CoverageItem] = Field(default_factory=list)
