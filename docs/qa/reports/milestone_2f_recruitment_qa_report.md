# Milestone 2F: Recruitment, Workforce Planning & Hiring Pipeline Dashboard QA Report

**Report Period:** 2026-06  
**Last Verified:** 2026-06-28  
**QA Status:** PASSED

---

## 1. Dashboard Overview
The Recruitment, Workforce Planning & Hiring Pipeline Dashboard provides complete row-level traceability, automated hiring SLA tracking, and audit-level data quality validation for:
- Requisition lifecycle (Open, Closed, Overdue status tracking)
- Candidates pipeline funnel stages
- Interview activities and scheduling validation
- Offer Acceptance rate and status breakdown
- Onboarding status monitoring and hire date mapping
- Workforce Plan fulfillment vs actual active headcount
- Recruitment exception audit log

---

## 2. Metric Verification (11 KPI Cards)
All 11 KPIs returned by `GET /api/recruitment/summary` reconcile exactly with the DuckDB database warehouse:

| KPI Key | Label | Value | Unit | Status |
| :--- | :--- | :---: | :---: | :---: |
| `open_requisitions` | Open Requisitions | **5.0** | requisitions | neutral |
| `approved_vacancies` | Approved Vacancies | **2.0** | vacancies | neutral |
| `candidates_in_pipeline` | Candidates in Pipeline | **6.0** | candidates | healthy |
| `interviews_scheduled` | Interviews Scheduled | **2.0** | interviews | neutral |
| `offers_extended` | Offers Extended | **3.0** | offers | neutral |
| `offer_acceptance_pct` | Offer Acceptance % | **100.0** | % | healthy |
| `hires_this_month` | Hires This Month | **1.0** | hires | neutral |
| `average_time_to_fill` | Average Time to Fill | **40.0** | days | healthy |
| `overdue_requisitions` | Overdue Requisitions | **1.0** | requisitions | critical |
| `workforce_plan_fulfillment_pct` | Workforce Plan Fulfillment % | **77.78** | % | warning |
| `recruitment_exception_count` | Recruitment Exception Count | **25.0** | alerts | critical |

---

## 3. API Endpoints Validation
All 11 endpoints under `/api/recruitment/*` have been captured and verified with live payloads:

### Endpoint Summaries
1. **`GET /api/recruitment/summary`**:
   - Returns 11 KPI items with HSL-tailored warning/critical thresholds.
2. **`GET /api/recruitment/pipeline`**:
   - Returns candidate stage funnel counts.
3. **`GET /api/recruitment/trends`**:
   - Compiles monthly requisitions opened vs hires.
4. **`GET /api/recruitment/by-project`**:
   - Lists requisitions count, open/closed counts, and overdue requisitions by project.
5. **`GET /api/recruitment/by-department`**:
   - Lists department-level requisitions and overdue metrics.
6. **`GET /api/recruitment/time-to-fill`**:
   - Lists average days to fill by project and department.
7. **`GET /api/recruitment/source-effectiveness`**:
   - Calculates conversion rates by sourcing channel (LinkedIn, Indeed, Referral, Direct, Agency, Other).
8. **`GET /api/recruitment/offers`**:
   - Returns counts for Offer Acceptances, Rejections, and Declines.
9. **`GET /api/recruitment/onboarding`**:
   - Lists onboarding stage count splits.
10. **`GET /api/recruitment/workforce-plan`**:
    - Calculates planned vs actual active headcount fulfillment by project and department.
11. **`GET /api/recruitment/exceptions`**:
    - Lists all 20 active exception checks.

---

## 4. Exception Log Details
The database flags **25 active issues** across the 20 required exception checks.

| Exception ID / Subject | Issue Type | Severity | Description / Recommended Action |
| :--- | :--- | :---: | :--- |
| **REQ003** | Missing Recruiter | Critical | Open requisition has no owner recruiter assigned. *Action: Assign a recruiter.* |
| **REQ004** | Overdue Requisition | Critical | Open requisition has breached its effective target date. *Action: Expedite sourcing.* |
| **REQ002** | Duplicate Requisition ID | Critical | Requisition ID REQ002 is logged multiple times. *Action: Deduplicate requisitions.* |
| **CAN002** | Duplicate Candidate ID | Critical | Candidate ID CAN002 is logged multiple times. *Action: Deduplicate candidates.* |
| **REQ005** | Empty Candidate Pipeline | Warning | Requisition is open but has 0 candidates linked. *Action: Link candidates.* |
| **CAN003** | Missing Pipeline Stage | Warning | Candidate has no pipeline stage logged. *Action: Assign stage.* |
| **CAN004** | Unknown Requisition Link | Critical | Candidate CAN004 links to REQ999 which is missing in master. *Action: Link correctly.* |
| **INT002** | Missing Interviewer | Warning | Interview has no interviewer assigned. *Action: Assign interviewer.* |
| **INT003** | Missing Interview Date | Warning | Interview record has no scheduled date. *Action: Set scheduled timestamp.* |
| **OFF002** | Offer Missing Salary | Critical | Offer extended has no base salary details. *Action: Enter salary details.* |
| **OFF003** | Onboarding Not Triggered | Critical | Offer status is Accepted but onboarding is not logged. *Action: Create onboarding record.* |
| **ONB002** | Unknown Employee ID | Warning | Onboarding links to employee EMP999 which is missing in directory. *Action: Check link.* |
| **Plan_Row** | Missing Plan Dimension | Warning | Workforce plan record has null project or department. *Action: Specify dimensions.* |
| **PROJ-ALPHA-Marketing** | Plan Exceeded | Warning | Actual headcount (2) exceeds planned headcount (0). *Action: Review plan.* |
| **PROJ-BETA-Engineering** | Plan Unfulfilled | Warning | Planned headcount (5) has not been fulfilled (Actual: 3). *Action: Sourcing push.* |
| **VAC003** | Invalid Vacancy Quantity | Critical | Vacancy request VAC003 has invalid quantity: -1. *Action: Set positive quantity.* |
| **CAN006** | Unknown Source Channel | Warning | Candidate has un-normalized source channel: Twitter. *Action: Map to standard channel.* |

---

## 5. Warehouse Reconciliation Log & Assertions
All 13 assertions run automatically inside `scripts/build_warehouse.py` during compilation. If a single check fails, the build pipeline fails.

### Recruitment Reconciliation Table

| Check ID | Assertion Objective | Verification Query / Formula | Value | Result |
| :--- | :--- | :--- | :---: | :---: |
| **Check 1** | Open Requisitions | `mart_recruitment_kpis.open_requisitions` = Open status count | **5** | **PASSED** |
| **Check 2** | Approved Vacancies | `mart_recruitment_kpis.approved_vacancies` = approved quantity sum | **2** | **PASSED** |
| **Check 3** | Candidates Pipeline | `mart_recruitment_kpis.candidates_in_pipeline` = active pipeline entries | **6** | **PASSED** |
| **Check 4** | Interviews Scheduled | `mart_recruitment_kpis.interviews_scheduled` = current month interviews | **2** | **PASSED** |
| **Check 5** | Offers Extended | `mart_recruitment_kpis.offers_extended` = current month offers | **3** | **PASSED** |
| **Check 6** | Offer Acceptance % | `offer_acceptance_pct` = accepted / decided offers ratio | **100%** | **PASSED** |
| **Check 7** | Hires This Month | `mart_recruitment_kpis.hires_this_month` = onboarding hires | **1** | **PASSED** |
| **Check 8** | Average Time to Fill | `average_time_to_fill` = average of hire_date - approval_date | **40.0** | **PASSED** |
| **Check 9** | Overdue Requisitions | `overdue_requisitions` = open requisitions past effective target | **1** | **PASSED** |
| **Check 10** | Workforce Plan Fulfillment | `fulfillment_pct` = actual active / planned headcount | **77.78%** | **PASSED** |
| **Check 11** | Project Requisition Sum | Sum of project requisitions = Total current requisitions | **7** | **PASSED** |
| **Check 12** | Dept Requisition Sum | Sum of department requisitions = Total current requisitions | **7** | **PASSED** |
| **Check 13** | Exception Count Check | `recruitment_exception_count` = Row count of exceptions view | **25** | **PASSED** |

---

## 6. Pipeline Outputs & Compilation Logs

### Python Data Pipeline (`python scripts/refresh_all.py`)
```text
Ingested recruitment_requisitions to bronze/silver.
Ingested candidates to bronze/silver.
Ingested interviews to bronze/silver.
Ingested offers to bronze/silver.
Ingested onboarding to bronze/silver.
Ingested workforce_plan to bronze/silver.
Ingested vacancy_requests to bronze/silver.
Ingestion complete.
Building DuckDB warehouse at warehouse/hr_analytics.duckdb...
Created view 'base_requisition_source_records'
Created view 'base_candidate_source_records'
Created view 'base_interview_source_records'
Created view 'base_offer_source_records'
Created view 'base_onboarding_source_records'
Created view 'base_recruitment_requisitions_current'
Created view 'base_candidate_canonical'
Created view 'base_candidate_pipeline_current'
Created view 'base_interview_activity_current'
Created view 'base_offer_activity_current'
Created view 'base_onboarding_current'
Created view 'base_workforce_plan_current'
Created view 'base_vacancy_population'
Created view 'mart_recruitment_exceptions'
Created view 'mart_recruitment_kpis'
Created view 'mart_recruitment_pipeline'
Created view 'mart_recruitment_trends'
Created view 'mart_recruitment_by_project'
Created view 'mart_recruitment_by_department'
Created view 'mart_recruitment_time_to_fill'
Created view 'mart_recruitment_source_effectiveness'
Created view 'mart_offer_acceptance'
Created view 'mart_onboarding_status'
Created view 'mart_workforce_plan_vs_actual'
Running Recruitment & Workforce Planning reconciliation checks...
Open Requisitions KPI: 5, Calculated: 5
Approved Vacancies KPI: 2, Calculated: 2
Candidates KPI: 6, Calculated: 6
Interviews KPI: 2, Calculated: 2
Offers KPI: 3, Calculated: 3
Offer Acceptance % KPI: 100.0, Expected: 100.0%
Hires KPI: 1, Calculated: 1
Time to Fill KPI: 40.0, Calculated: 40.0
Overdue Requisitions KPI: 1, Calculated: 1
Workforce Plan Fulfillment % KPI: 77.78, Expected: 77.78%
Sum Project Requisitions: 7, Total Requisitions: 7
Sum Department Requisitions: 7, Total Requisitions: 7
Recruitment Exception Count KPI: 25, Calculated: 25
Reconciliation checks PASSED.
DuckDB database warehouse creation complete.
```
