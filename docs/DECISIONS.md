# Architecture & Technical Decisions

## 1. Local-First Analytics Stack
- **Decision**: Use Polars + DuckDB.
- **Rationale**: Polars provides extremely fast schema validation and Parquet output. DuckDB offers embedded relational capabilities over Parquet files, making it the perfect engine to run analytics SQL locally.

## 2. Calculation Separation (No Frontend Math)
- **Decision**: Official calculations are computed in DuckDB analytical views or Python services.
- **Rationale**: Keeps React code clean and prevents discrepancies between different dashboard sheets.

## 3. Tailwind CSS & Custom Components
- **Decision**: Avoid installing full shadcn/ui library initially. Build clean reusable components with Tailwind CSS.
- **Rationale**: Eliminates complex setup scripts or dependencies while maintaining modular components that can be migrated to shadcn/ui components later.

## 4. Analytical Views for KPI Data
- **Decision**: Use DuckDB views (`mart_exec_kpis`, `mart_exec_trends`, `mart_data_quality_summary`, `mart_data_quality_exceptions`) instead of dynamic Python math on backend retrieval.
- **Rationale**: Leverages the speed of SQL transformations and allows easy future migration to dbt-based pipelines.

## 5. Iqama Expiry Preferred Source
- **Decision**: Retrieve `iqama_expiry` from the `compliance` table by joining on `employee_id`.
- **Rationale**: Keeps compliance certifications and employee demographic profile data separated in the source schema, using `employee_id` as the relational key.

## 6. Numeric JSON Keys Serialization via Pydantic Aliases
- **Decision**: Use Pydantic V2 `Field(..., alias="...")` and `model_config = {"populate_by_name": True}` to serialize numerical keys (e.g. `"0_30"`).
- **Rationale**: Standard Python identifier rules prevent variables starting with numbers. Aliases enable returning exact compliant JSON schema structures to the frontend without any custom translation logic in React.

## 7. Canonical Deduplicated Active Workforce View
- **Decision**: Create a base view `base_active_workforce` which filters by `status = 'Active'` and deduplicates the active employee entries by `employee_id` using a consistent ordering (selecting the latest joining/contract end date entry).
- **Rationale**: Prevents data inflation in categorical distributions and expiry buckets caused by duplicate employee keys in raw logs, guaranteeing perfect mathematical reconciliation between active headcount and demographic totals (sums equal exactly 19).

## 8. Separation of Payroll Record Base and Active Workforce Join
- **Decision**: Build payroll views starting from payroll records first, then left-joining to employee attributes.
- **Rationale**: Ensures that payroll costs for terminated or inactive employees (who might have final pay checks) are fully captured and accounted for in the total cost metrics, preventing cost discrepancies. If employee attributes are missing, they default to standard categories ("Missing Department", "Inactive/Terminated/Unknown").

## 9. Configurable Variance Thresholds
- **Decision**: Define variance rule parameters (Gross amount limit: 2000 SAR, Basic pct change: 10%) inside `config/metrics_dictionary.yml` instead of hardcoding values inside SQL or API logic.
- **Rationale**: Keeps dashboard thresholds easily adjustable by business administrators without requiring code edits or database schema modifications.

## 10. Multi-Layer Reconciliation Validation
- **Decision**: Implement strict programmatic assertions inside the data build script `build_warehouse.py` checking math formulas and distribution totals.
- **Rationale**: Fails the warehouse compilation script if any discrepancies exist (e.g. project totals, paid counts, components, net sums), preventing corrupt data from ever reaching the live API.

## 11. Expected Workdays Denominator for Compliance and Absence
- **Decision**: Generate expected workday calendars dynamically by cross-joining report month date ranges with employees active on those calendar dates, filtering out weekends. Use this calendar as the denominator for attendance compliance, absences, and missing punch calculations.
- **Rationale**: Prevents data bias in compliance scores and accurately catches absent employees who have no punch logs. Using raw attendance rows as the denominator would skew calculations because absences would have no row.

## 12. Configurable Lateness Grace Period and Calculated Late Minutes
- **Decision**: Define working parameters (such as `grace_period_minutes: 15` and `weekend_days: ["Friday"]`) in `config/business_rules.yml`. Derive official lateness from shift scheduled start and check-in times:
  `calculated_late_minutes = GREATEST(date_diff('minute', scheduled_start, actual_check_in) - grace_period_minutes, 0)`
  `calculated_net_late_minutes = GREATEST(calculated_late_minutes - excused_late_minutes, 0)`
  Do not use the source `late_minutes` or `net_late_minutes` directly as the official metrics; they are only used for comparison validation.
- **Rationale**: Ensures that official lateness is computed using standardized rules and parameters rather than raw logs. It also flags a validation exception when raw log data deviates from expected parameters.

## 13. Leave and Holiday Exclusions Limitations
- **Decision**: Document leave and holiday exclusion as structurally supported but not active in MVP due to the absence of leave/holiday source tables.
- **Rationale**: Adheres to the actual data schema constraints without pretending exclusions are active, documenting this as a known limitation.

## 14. Stable Analytical Keys & Pre-filter Source Views (Milestone 2F)
- **Decision**: Create source-level views (`base_requisition_source_records`, `base_candidate_source_records`, etc.) to generate deterministic row-level keys (e.g. `requisition_record_id`, `candidate_record_id`) via row number ordering. Join base views using these keys or canonical deduplicated records rather than raw business IDs.
- **Rationale**: Business identifiers like `requisition_id` or `candidate_id` are prone to duplication in source records (which are flagged as exceptions). Joining directly on business IDs would multiply row counts in analytical views, skewing aggregate totals. Row-level keys protect the integrity of joins, while pre-filter views allow us to audit and capture invalid reference exceptions (e.g. candidate linked to unknown requisition) before applying report filters.

## 15. Simulated Trends for MVP Visuals (Milestone 2F)
- **Decision**: The recruitment trends view `mart_recruitment_trends` simulates historical data rows for periods `2026-04` and `2026-05` to render visual trend lines in the MVP dashboard. The current period `2026-06` is resolved dynamically from live seed records.
- **Rationale**: Sourcing and hiring trends require historical comparison periods to be visually informative. Rather than faking the entire database, we overlay historical points in the final mart view while keeping the underlying source data clean and fully reconcilable for the current report period. This is documented as sample-mode only.
