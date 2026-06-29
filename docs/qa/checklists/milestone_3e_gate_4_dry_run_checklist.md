# Milestone 3E - Gate 4 Dry-Run Checklist

This checklist confirms the verification of dry-run parameters across all 8 operational categories.

---

## 1. Category Checklist

*   [x] **HRIS / Employee Master**: File path, expected columns, valid counts, and check constraints verified.
*   [x] **Payroll**: Basic salary, gross pay, deductions, and net equations verified.
*   [x] **Attendance**: Badges, checks, date ranges, and tardy minutes verified.
*   [x] **Government / Compliance**: Saudization rates and WPS statuses verified.
*   [x] **Employee Relations / Case Management**: Case ID, subject employee, status, and invalid date logic verified.
*   [x] **Recruitment / Workforce Planning**: Requisitions, offers, hires, and fulfillment rates verified.
*   [x] **Talent / Performance / Learning**: Ratings, completion statuses, and opaque candidate key rules verified.
*   [x] **Data Quality / Command Center Metadata**: Core modules, API checks, and freshness metrics verified.

---

## 2. Validation Constraints Verified

*   [x] Valid synthetic files pass validation cleanly.
*   [x] Duplicate or blank employee IDs trigger quarantine routing.
*   [x] Net pay mismatch or negative salaries trigger file rejection.
*   [x] Raw Iqamas, IBAN patterns, or credentials trigger file rejection.
