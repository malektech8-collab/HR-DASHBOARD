# HR Command Center — Source System Inventory

This document registers all operational systems and delivery details required for the HR Analytics Command Center integration, mapping them to the owner matrix roles.

---

## 1. HRIS / Employee Master System
*   **`source_system_id`**: `src_hris_employee`
*   **`source_system_name`**: `Jisr HR Portal`
*   **`source_category`**: `HRIS / Employee Master`
*   **`business_owner`**: `HR Director` (linked to matrix)
*   **`technical_owner`**: `IT Operations Lead` (linked to matrix)
*   **`data_steward`**: `HR Operations Administrator` (linked to matrix)
*   **`refresh_frequency`**: `Daily`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `SFTP Upload`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["executive", "workforce", "compliance", "talent"]`
*   **`known_data_quality_risks`**: `Manual input typos in Arabic/English names, missing cost centers`
*   **`readiness_status`**: `Steward Validated`
*   **`notes`**: `Provides base workforce reference records.`

---

## 2. ERP / Payroll Ledger
*   **`source_system_id`**: `src_payroll_netsuite`
*   **`source_system_name`**: `NetSuite ERP Financials`
*   **`source_category`**: `Payroll`
*   **`business_owner`**: `Finance Director` (linked to matrix)
*   **`technical_owner`**: `ERP Systems Administrator` (linked to matrix)
*   **`data_steward`**: `Payroll Manager` (linked to matrix)
*   **`refresh_frequency`**: `Monthly`
*   **`expected_file_format`**: `Excel (XLSX)`
*   **`delivery_method`**: `SFTP Upload`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["executive", "payroll", "compliance"]`
*   **`known_data_quality_risks`**: `Unregistered manual payroll adjustments or currency conversions`
*   **`readiness_status`**: `Awaiting Signoff`
*   **`notes`**: `Provides payroll ledger details.`

---

## 3. Biometric Attendance
*   **`source_system_id`**: `src_attendance_biometric`
*   **`source_system_name`**: `ZK Teco Biometric Attendance Portal`
*   **`source_category`**: `Attendance`
*   **`business_owner`**: `HR Operations Manager` (linked to matrix)
*   **`technical_owner`**: `Facilities Network Engineer` (linked to matrix)
*   **`data_steward`**: `Attendance Clerk` (linked to matrix)
*   **`refresh_frequency`**: `Daily`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `Local Upload`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `No`
*   **`approval_required`**: `No`
*   **`source_of_truth_priority`**: `2`
*   **`downstream_modules`**: `["attendance"]`
*   **`known_data_quality_risks`**: `Network timeout on card readers causing missing punch outs`
*   **`readiness_status`**: `Ready for Test Load`
*   **`notes`**: `Requires manual check validations for daily entries.`

---

## 4. Government Portals
*   **`source_system_id`**: `src_gov_compliance`
*   **`source_system_name`**: `Qiwa / GOSI Government Portals`
*   **`source_category`**: `Government / Compliance`
*   **`business_owner`**: `Government Relations Officer` (linked to matrix)
*   **`technical_owner`**: `G2B Integration Architect` (linked to matrix)
*   **`data_steward`**: `Compliance Manager` (linked to matrix)
*   **`refresh_frequency`**: `Weekly`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `Manual Portal Download / SFTP`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["compliance"]`
*   **`known_data_quality_risks`**: `Synchronization lag on national ID expirations`
*   **`readiness_status`**: `Steward Validated`
*   **`notes`**: `Provides GOSI and Qiwa status mappings.`

---

## 5. SharePoint ER Case Tracker
*   **`source_system_id`**: `src_er_case_tracker`
*   **`source_system_name`**: `SharePoint ER Tracker`
*   **`source_category`**: `Employee Relations / Case Management`
*   **`business_owner`**: `Employee Relations Manager` (linked to matrix)
*   **`technical_owner`**: `SharePoint Administrator` (linked to matrix)
*   **`data_steward`**: `ER Coordinator` (linked to matrix)
*   **`refresh_frequency`**: `Daily`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `SFTP`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["er"]`
*   **`known_data_quality_risks`**: `Unredacted description narratives containing legal disputes`
*   **`readiness_status`**: `Steward Validated`
*   **`notes`**: `Requires manual redacting check prior to file upload.`

---

## 6. Lever ATS
*   **`source_system_id`**: `src_recruitment_ats`
*   **`source_system_name`**: `Lever ATS`
*   **`source_category`**: `Recruitment / Workforce Planning`
*   **`business_owner`**: `Head of Talent Acquisition` (linked to matrix)
*   **`technical_owner`**: `ATS Integration Engineer` (linked to matrix)
*   **`data_steward`**: `Recruitment Coordinator` (linked to matrix)
*   **`refresh_frequency`**: `Daily`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `SFTP`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `No`
*   **`approval_required`**: `No`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["recruitment"]`
*   **`known_data_quality_risks`**: `Candidate name and offer values must be pseudonymized`
*   **`readiness_status`**: `Ready for Test Load`
*   **`notes`**: `Maps candidates and vacancy funnels.`

---

## 7. Learning Management System
*   **`source_system_id`**: `src_talent_lms`
*   **`source_system_name`**: `Coursera LMS / SuccessFactors`
*   **`source_category`**: `Talent / Performance / Learning`
*   **`business_owner`**: `Talent & Development Director` (linked to matrix)
*   **`technical_owner`**: `LMS Systems Lead` (linked to matrix)
*   **`data_steward`**: `L&D Coordinator` (linked to matrix)
*   **`refresh_frequency`**: `Weekly`
*   **`expected_file_format`**: `Excel (XLSX)`
*   **`delivery_method`**: `SFTP`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["talent"]`
*   **`known_data_quality_risks`**: `Competency mapping discrepancies across job profiles`
*   **`readiness_status`**: `Draft`
*   **`notes`**: `Maps training hours, goal metrics, ratings, and succession pipelines.`

---

## 8. Metadata Engine
*   **`source_system_id`**: `src_metadata_engine`
*   **`source_system_name`**: `Command Center Audit Engine`
*   **`source_category`**: `Data Quality / Command Center Metadata`
*   **`business_owner`**: `HR Systems Lead` (linked to matrix)
*   **`technical_owner`**: `Antigravity Systems Architect` (linked to matrix)
*   **`data_steward`**: `Data Quality Engineer` (linked to matrix)
*   **`refresh_frequency`**: `Daily`
*   **`expected_file_format`**: `CSV`
*   **`delivery_method`**: `SFTP`
*   **`contains_personal_data`**: `Yes`
*   **`contains_sensitive_data`**: `Yes`
*   **`approval_required`**: `Yes`
*   **`source_of_truth_priority`**: `1`
*   **`downstream_modules`**: `["executive", "data-quality"]`
*   **`known_data_quality_risks`**: `DuckDB lock contention during parallel uvicorn writes`
*   **`readiness_status`**: `Ready for Test Load`
*   **`notes`**: `Central metadata engine for monitoring freshness, quality exceptions, and alerts.`
