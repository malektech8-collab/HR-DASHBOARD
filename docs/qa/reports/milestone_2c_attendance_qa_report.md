# Milestone 2C: Attendance, Absence & Overtime Dashboard QA Report

**Generated**: 2026-06-25  
**Report Month**: 2026-06  
**Data Source**: All values derived live from API endpoints; no hardcoded values.  
**Data Integrity**: No real HR data or employee records were used. All inputs are synthetic sample data.

---

## 1. Dashboard Screenshot

The dashboard has been verified and captured:
- **Screenshot Path**: `docs/qa/screenshots/milestone_2c_attendance_dashboard.png`

---

## 2. Pipeline Execution

```
python scripts/refresh_all.py
```

| Step | Result |
|:---|:---|
| Generate sample data | PASSED |
| Ingest CSVs to Parquet (bronze/silver) | PASSED |
| Validate silver Parquet files | PASSED (15 DQ issues) |
| Build DuckDB warehouse (views + reconciliation) | PASSED |

All 8 attendance reconciliation assertions passed with zero discrepancy.

---

## 3. Files Created & Changed

| File | Action | Purpose |
|:---|:---|:---|
| `config/business_rules.yml` | **NEW** | Defined grace period (15 min), weekend days (Friday), report month source. |
| `scripts/build_warehouse.py` | **MODIFY** | Created 4 base views, 8 attendance marts, 8 reconciliation assertions. |
| `backend/app/schemas/attendance.py` | **NEW** | Response models for all attendance API payloads. |
| `backend/app/api/attendance.py` | **NEW** | 8 REST API routes serving attendance dashboard metrics. |
| `backend/app/main.py` | **MODIFY** | Registered `/api/attendance` router prefix. |
| `frontend/src/lib/types.ts` | **MODIFY** | TypeScript interfaces for attendance API responses. |
| `frontend/src/lib/api.ts` | **MODIFY** | Attendance API fetcher functions. |
| `frontend/src/pages/Attendance.tsx` | **MODIFY** | 10 KPI cards, ECharts graphs, exceptions table. |
| `frontend/src/components/layout/SidebarNavigation.tsx` | **MODIFY** | Activated Attendance sidebar link. |
| `docs/DATA_MODEL.md` | **MODIFY** | Documented 12 new database views. |
| `docs/METRICS_DICTIONARY.md` | **MODIFY** | Documented attendance metric definitions. |
| `docs/DEVELOPMENT_LOG.md` | **MODIFY** | Appended Milestone 2C log entry. |
| `docs/DECISIONS.md` | **MODIFY** | Logged design decisions. |

---

## 4. DuckDB Views Created

### Base Views
1. **`base_employees_deduplicated`** — Deduplicated master list prioritizing Active entries for duplicate employee IDs.
2. **`base_attendance_current`** — Attendance logs filtered by report month, left-joined to employee metadata. Calculates `calculated_late_minutes` and `calculated_net_late_minutes` using 15-min grace period.
3. **`base_expected_attendance`** — Cross-join of report month calendar dates with active employees (filtered by joining/termination dates and weekends). Left-joins attendance punches to identify absences.
4. **`base_attendance_payroll_overtime`** — Full outer join of attendance overtime hours with payroll overtime cost per employee.

### Mart Views
5. **`mart_attendance_exceptions`** — 14 exception checks consolidated into a single audit log.
6. **`mart_attendance_kpis`** — Pre-computed summary KPIs for the dashboard.
7. **`mart_attendance_trend`** — 3-month trend of compliance, absences, lateness.
8. **`mart_attendance_by_project`** — Compliance and overtime by project.
9. **`mart_attendance_by_department`** — Compliance, lateness, and overtime by department.
10. **`mart_attendance_late_arrival`** — Employee-level late arrival log.
11. **`mart_attendance_overtime`** — Employee-level overtime reconciliation.
12. **`mart_attendance_missing_punches`** — Employee-level missing check-in/check-out counts.

---

## 5. Reconciliation Verification Table

| # | Check Description | Target Metric | Reconciled Metric | Discrepancy | Status |
|:---|:---|:---|:---|:---|:---|
| 1 | Expected Workdays | `base_expected_attendance` = `494` | Generated calendar = `494` | `0` | **PASSED** |
| 2 | Absence Days | `mart_attendance_kpis` = `419.0` | Expected without punches = `419` | `0.0` | **PASSED** |
| 3 | Late Minutes | `mart_attendance_kpis` = `30` | `base_attendance_current` = `30` | `0.0` | **PASSED** |
| 4 | Net Late Minutes Math | `net_late = GREATEST(late - excused, 0)` | Mismatch count = `0` | `0` | **PASSED** |
| 5 | Missing Punch Count | `mart_attendance_kpis` = `1` | Missing punch exceptions = `1` | `0` | **PASSED** |
| 6 | Approved Overtime Hours | `mart_attendance_kpis` = `2.5` | `base_ot_reconciliation` = `2.5` | `0.0` | **PASSED** |
| 7 | Payroll Overtime Cost | `mart_attendance_kpis` = `2900.0` | `base_ot_reconciliation` = `2900.0` | `0.0` | **PASSED** |
| 8 | Attendance Exception Count | `mart_attendance_kpis` = `430` | Exception table rows = `430` | `0` | **PASSED** |

---

## 6. Missing Punch Reconciliation (Detailed)

### 6.1 Exception Breakdown by Issue Type

The `mart_attendance_exceptions` view contains 14 checks. The 430 total exceptions break down as:

| Issue Type | Count | Category |
|:---|:---|:---|
| Missing Workday Attendance | 418 | Missing attendance record for expected workday |
| Overtime Hours Missing | 7 | Payroll overtime without attendance OT hours |
| Missing Check-out | 1 | Missing punch event |
| One Punch Only | 1 | Missing punch event |
| Source Late Minutes Mismatch | 1 | Source data reconciliation |
| Source Net Late Minutes Mismatch | 1 | Source data reconciliation |
| Overtime Amount Missing | 1 | Attendance OT without payroll payment |
| **TOTAL** | **430** | |

### 6.2 Missing Punch vs. Missing Workday Attendance Distinction

| Metric | Definition | Count |
|:---|:---|:---|
| **Missing Check-in** | Employee has check-out but no check-in on an attendance record | 0 |
| **Missing Check-out** | Employee has check-in but no check-out on an attendance record | 1 |
| **Both Punches Missing** | Attendance record exists but both check-in and check-out are NULL and absence_days = 0 | 0 |
| **One Punch Only** | Exactly one of check-in or check-out is present (union of missing check-in + missing check-out) | 1 |
| **Missing Workday Attendance** | Active employee has no attendance record at all for an expected workday (from `base_expected_attendance` where `attendance_date IS NULL`) | 418 |

> [!IMPORTANT]
> **Missing punch events** (1 total) are attendance records that exist but have incomplete punch data (check-in or check-out missing).
>
> **Missing attendance records** (418 total) are expected workdays where no attendance record exists at all for an active employee. These are not "missing punches" — they are entirely absent records.
>
> The KPI card "Missing Punch Count" (value: 1) counts only **missing punch events**, not missing attendance records. Missing attendance records are counted separately under "Absence Days" and "Missing Workday Attendance" exceptions.

### 6.3 Missing Punches API Detail

```json
{
  "missing_punches": [
    {
      "employee_id": "EMP002",
      "employee_name": "John Doe",
      "department": "Engineering",
      "project": "PROJ-BETA",
      "missing_check_in_count": 0,
      "missing_check_out_count": 1,
      "total_missing_punches": 1
    }
  ]
}
```

---

## 7. API Endpoint Outputs (All 8 Endpoints)

### 7.1 `GET /api/attendance/summary`

```json
{
  "report_month": "2026-06",
  "kpis": [
    {
      "key": "attendance_compliance_pct",
      "label": "Attendance Compliance %",
      "value": 14.78,
      "unit": "%",
      "trend_value": null,
      "trend_direction": null,
      "status": "critical"
    },
    {
      "key": "absence_days",
      "label": "Absence Days",
      "value": 419.0,
      "unit": "days",
      "trend_value": null,
      "trend_direction": null,
      "status": "warning"
    },
    {
      "key": "late_minutes",
      "label": "Late Minutes",
      "value": 30.0,
      "unit": "min",
      "trend_value": null,
      "trend_direction": null,
      "status": "healthy"
    },
    {
      "key": "excused_late_minutes",
      "label": "Excused Late Minutes",
      "value": 15.0,
      "unit": "min",
      "trend_value": null,
      "trend_direction": null,
      "status": "neutral"
    },
    {
      "key": "net_late_minutes",
      "label": "Net Late Minutes",
      "value": 15.0,
      "unit": "min",
      "trend_value": null,
      "trend_direction": null,
      "status": "healthy"
    },
    {
      "key": "early_leave_minutes",
      "label": "Early Leave Minutes",
      "value": 0.0,
      "unit": "min",
      "trend_value": null,
      "trend_direction": null,
      "status": "healthy"
    },
    {
      "key": "missing_punch_count",
      "label": "Missing Punch Count",
      "value": 1.0,
      "unit": "punches",
      "trend_value": null,
      "trend_direction": null,
      "status": "critical"
    },
    {
      "key": "overtime_hours",
      "label": "Overtime Hours",
      "value": 2.5,
      "unit": "hrs",
      "trend_value": null,
      "trend_direction": null,
      "status": "neutral"
    },
    {
      "key": "overtime_cost",
      "label": "Overtime Cost",
      "value": 2900.0,
      "unit": "SAR",
      "trend_value": null,
      "trend_direction": null,
      "status": "neutral"
    },
    {
      "key": "attendance_exception_count",
      "label": "Attendance Exception Count",
      "value": 430.0,
      "unit": "issues",
      "trend_value": null,
      "trend_direction": null,
      "status": "critical"
    }
  ]
}
```

### 7.2 `GET /api/attendance/trends`

```json
{
  "trends": [
    {
      "month": "2026-04",
      "attendance_compliance_pct": 96.5,
      "absence_days": 2.0,
      "late_minutes": 180.0,
      "net_late_minutes": 120.0,
      "missing_punch_count": 1.0,
      "overtime_hours": 8.0
    },
    {
      "month": "2026-05",
      "attendance_compliance_pct": 95.0,
      "absence_days": 3.0,
      "late_minutes": 240.0,
      "net_late_minutes": 180.0,
      "missing_punch_count": 2.0,
      "overtime_hours": 12.5
    },
    {
      "month": "2026-06",
      "attendance_compliance_pct": 14.78,
      "absence_days": 419.0,
      "late_minutes": 30.0,
      "net_late_minutes": 15.0,
      "missing_punch_count": 1.0,
      "overtime_hours": 2.5
    }
  ]
}
```

### 7.3 `GET /api/attendance/by-project`

```json
{
  "projects": [
    {
      "project": "PROJ-GAMMA",
      "headcount": 6,
      "attendance_compliance_pct": 15.38,
      "absence_days": 132.0,
      "late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 2.5,
      "overtime_cost": 900.0
    },
    {
      "project": "PROJ-BETA",
      "headcount": 3,
      "attendance_compliance_pct": 14.1,
      "absence_days": 66.0,
      "late_minutes": 0.0,
      "missing_punches": 1,
      "overtime_hours": 0.0,
      "overtime_cost": 1100.0
    },
    {
      "project": "Missing Project",
      "headcount": 1,
      "attendance_compliance_pct": 11.54,
      "absence_days": 23.0,
      "late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 0.0
    },
    {
      "project": "PROJ-ALPHA",
      "headcount": 9,
      "attendance_compliance_pct": 14.96,
      "absence_days": 198.0,
      "late_minutes": 30.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 900.0
    }
  ]
}
```

### 7.4 `GET /api/attendance/by-department`

```json
{
  "departments": [
    {
      "department": "Finance",
      "headcount": 2,
      "attendance_compliance_pct": 13.46,
      "absence_days": 44.0,
      "late_minutes": 30.0,
      "net_late_minutes": 15.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 300.0
    },
    {
      "department": "Engineering",
      "headcount": 4,
      "attendance_compliance_pct": 14.42,
      "absence_days": 88.0,
      "late_minutes": 0.0,
      "net_late_minutes": 0.0,
      "missing_punches": 1,
      "overtime_hours": 0.0,
      "overtime_cost": 1100.0
    },
    {
      "department": "HR",
      "headcount": 4,
      "attendance_compliance_pct": 15.38,
      "absence_days": 88.0,
      "late_minutes": 0.0,
      "net_late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 1100.0
    },
    {
      "department": "Executive",
      "headcount": 1,
      "attendance_compliance_pct": 15.38,
      "absence_days": 22.0,
      "late_minutes": 0.0,
      "net_late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 0.0
    },
    {
      "department": "Marketing",
      "headcount": 3,
      "attendance_compliance_pct": 14.1,
      "absence_days": 67.0,
      "late_minutes": 0.0,
      "net_late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 0.0,
      "overtime_cost": 0.0
    },
    {
      "department": "Operations",
      "headcount": 5,
      "attendance_compliance_pct": 15.38,
      "absence_days": 110.0,
      "late_minutes": 0.0,
      "net_late_minutes": 0.0,
      "missing_punches": 0,
      "overtime_hours": 2.5,
      "overtime_cost": 400.0
    }
  ]
}
```

### 7.5 `GET /api/attendance/late-arrival`

```json
{
  "late_arrivals": [
    {
      "employee_id": "EMP003",
      "employee_name": "Fahad Al-Otaibi",
      "department": "Finance",
      "project": "PROJ-ALPHA",
      "total_late_minutes": 30,
      "total_excused_minutes": 15,
      "total_net_late_minutes": 15,
      "late_arrival_incidents_count": 1
    }
  ]
}
```

### 7.6 `GET /api/attendance/overtime`

```json
{
  "overtime_records": [
    {
      "employee_id": "EMP005",
      "employee_name": "Khalid Al-Ghamdi",
      "department": "Operations",
      "project": "PROJ-GAMMA",
      "attendance_ot_hours": 2.5,
      "payroll_ot_cost": 0.0,
      "reconciliation_status": "OT in Attendance only"
    },
    {
      "employee_id": "EMP001",
      "employee_name": "Ahmad Al-Sudairy",
      "department": "HR",
      "project": "PROJ-ALPHA",
      "attendance_ot_hours": 0.0,
      "payroll_ot_cost": 450.0,
      "reconciliation_status": "OT in Payroll only"
    }
  ]
}
```

> Full output contains 20 overtime records. Reconciliation status breakdown:
>
> | Status | Count |
> |:---|:---|
> | No Overtime | 12 |
> | OT in Payroll only | 7 |
> | OT in Attendance only | 1 |
> | **TOTAL** | **20** |

### 7.7 `GET /api/attendance/missing-punches`

```json
{
  "missing_punches": [
    {
      "employee_id": "EMP002",
      "employee_name": "John Doe",
      "department": "Engineering",
      "project": "PROJ-BETA",
      "missing_check_in_count": 0,
      "missing_check_out_count": 1,
      "total_missing_punches": 1
    }
  ]
}
```

### 7.8 `GET /api/attendance/exceptions`

Total exception records: **430**

Full breakdown by issue type:

| Issue Type | Count | Severity | Description |
|:---|:---|:---|:---|
| Missing Workday Attendance | 418 | Warning | Active employee has no attendance record for expected workday |
| Overtime Hours Missing | 7 | Critical | Payroll overtime payment exists but no approved OT hours in attendance |
| Missing Check-out | 1 | Warning | Employee has check-in but check-out is missing |
| One Punch Only | 1 | Warning | Only one of check-in or check-out is recorded |
| Source Late Minutes Mismatch | 1 | Warning | Source system late minutes differs from calculated late minutes |
| Source Net Late Minutes Mismatch | 1 | Warning | Source system net late minutes differs from calculated value |
| Overtime Amount Missing | 1 | Critical | Employee has approved OT hours but payroll OT amount is zero |
| **TOTAL** | **430** | | |

Sample exception record:
```json
{
  "employee_id": "EMP002",
  "employee_name": "John Doe",
  "issue_type": "Missing Check-out",
  "description": "Employee has actual check-in but actual check-out is missing on 2026-06-10",
  "severity": "Warning",
  "recommended_action": "Request employee to provide check-out time"
}
```

---

## 8. 10 KPI Cards Confirmed

| # | KPI | Value | Unit | Status |
|:---|:---|:---|:---|:---|
| 1 | Attendance Compliance % | 14.78 | % | critical |
| 2 | Absence Days | 419.0 | days | warning |
| 3 | Late Minutes | 30.0 | min | healthy |
| 4 | Excused Late Minutes | 15.0 | min | neutral |
| 5 | Net Late Minutes | 15.0 | min | healthy |
| 6 | Early Leave Minutes | 0.0 | min | healthy |
| 7 | Missing Punch Count | 1.0 | punches | critical |
| 8 | Overtime Hours | 2.5 | hrs | neutral |
| 9 | Overtime Cost | 2,900.0 | SAR | neutral |
| 10 | Attendance Exception Count | 430.0 | issues | critical |

---

## 9. Build Verification

```
npm run build
```

Result: **PASSED** (production build completed successfully)

---

## 10. Known Limitations

1. **Leave and Holiday Handling**: Leave and holiday exclusion is structurally supported in SQL view models but not active until leave/holiday source tables are added. Currently, expected workdays are computed solely by filtering active employee periods and configured weekends.
2. **Shift Schedules**: Shift scheduled start/end times are assumed uniform across shifts in sample dataset.
3. **Low Compliance %**: The 14.78% compliance rate is expected for sample data — only a few attendance records exist against 494 expected workdays for 19 active employees.

---

## 11. Architecture Compliance

- No calculations in React. React displays pre-computed API values only.
- All metrics computed in DuckDB SQL views (`base_*` and `mart_*`).
- `base_expected_attendance` generates the calendar denominator via employee-date cross-join.
- Grace period (15 min) and weekend days (Friday) are configurable via `config/business_rules.yml`.

> [!IMPORTANT]
> Antigravity confirms that no real HR data or employee records were used. All inputs, calculations, and tests are built on synthetic, randomized sample data profiles.
