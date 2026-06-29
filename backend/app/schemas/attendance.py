from pydantic import BaseModel
from typing import List, Optional
from app.schemas.kpi import KPIItem, DQExceptionItem

class AttendanceSummaryResponse(BaseModel):
    report_month: str
    kpis: List[KPIItem]

class AttendanceTrendItem(BaseModel):
    month: str
    attendance_compliance_pct: float
    absence_days: float
    late_minutes: float
    net_late_minutes: float
    missing_punch_count: float
    overtime_hours: float

class AttendanceTrendsResponse(BaseModel):
    trends: List[AttendanceTrendItem]

class AttendanceByProjectItem(BaseModel):
    project: str
    headcount: int
    attendance_compliance_pct: float
    absence_days: float
    late_minutes: float
    missing_punches: int
    overtime_hours: float
    overtime_cost: float

class AttendanceByProjectResponse(BaseModel):
    projects: List[AttendanceByProjectItem]

class AttendanceByDepartmentItem(BaseModel):
    department: str
    headcount: int
    attendance_compliance_pct: float
    absence_days: float
    late_minutes: float
    net_late_minutes: float
    missing_punches: int
    overtime_hours: float
    overtime_cost: float

class AttendanceByDepartmentResponse(BaseModel):
    departments: List[AttendanceByDepartmentItem]

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
    late_arrivals: List[AttendanceLateArrivalItem]

class AttendanceOvertimeItem(BaseModel):
    employee_id: str
    employee_name: Optional[str] = None
    department: Optional[str] = None
    project: Optional[str] = None
    attendance_ot_hours: float
    payroll_ot_cost: float
    reconciliation_status: str

class AttendanceOvertimeResponse(BaseModel):
    overtime_records: List[AttendanceOvertimeItem]

class AttendanceMissingPunchesItem(BaseModel):
    employee_id: str
    employee_name: str
    department: Optional[str] = None
    project: Optional[str] = None
    missing_check_in_count: int
    missing_check_out_count: int
    total_missing_punches: int

class AttendanceMissingPunchesResponse(BaseModel):
    missing_punches: List[AttendanceMissingPunchesItem]

class AttendanceExceptionsResponse(BaseModel):
    exceptions: List[DQExceptionItem]
