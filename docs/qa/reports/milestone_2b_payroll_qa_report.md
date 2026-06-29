# Milestone 2B: Payroll & Cost Dashboard QA Report

This report documents the programmatic QA verification of the Payroll & Cost Dashboard. All metrics are compiled dynamically from the live API endpoints during the validation process.

---

## 1. Verified KPI Cards (Total: 10)

| KPI Card | Key | Value | Source Endpoint |
| :--- | :--- | :--- | :--- |
| **Total Payroll Cost** | `total_payroll_cost` | `446,175.00 SAR` | `/api/payroll/summary` |
| **Net Payroll** | `net_payroll` | `437,475.00 SAR` | `/api/payroll/summary` |
| **Employees Paid** | `employees_paid` | `20` | `/api/payroll/summary` |
| **Average Cost per Employee** | `avg_cost_per_employee` | `22,308.75 SAR` | `/api/payroll/summary` |
| **Payroll Variance vs Previous Month** | `payroll_variance_pct` | `-0.05%` | `/api/payroll/summary` |
| **Basic Salary Cost** | `basic_salary_cost` | `323,500.00 SAR` | `/api/payroll/summary` |
| **Allowances Cost** | `allowances_cost` | `120,275.00 SAR` | `/api/payroll/summary` |
| **Overtime Cost** | `overtime_cost` | `2,900.00 SAR` | `/api/payroll/summary` |
| **Deductions** | `deductions` | `8,700.00 SAR` | `/api/payroll/summary` |
| **Payroll Exception Count** | `payroll_exception_count` | `15` | `/api/payroll/summary` |


---

## 2. Payroll Component Breakdown

Below is the full payroll component breakdown compiled from `/api/payroll/components`:

| Component Name | Amount |
| :--- | :--- |
| **Basic Salary** | 323,500.00 SAR |
| **Housing Allowance** | 82,875.00 SAR |
| **Transport Allowance** | 27,500.00 SAR |
| **Other Allowances** | 9,900.00 SAR |
| **Overtime** | 2,900.00 SAR |
| **Deductions** | 8,700.00 SAR |
| **Unreconciled / Exception Amount** | -500.00 SAR |


---

## 3. Payroll Reconciliation Table

Below is the verified reconciliation table generated from the analytical warehouse database view `mart_payroll_reconciliation`:

| Metric Name | Reconciled Value | Source Formula / Explanation |
| :--- | :--- | :--- |
| **Total Gross Payroll** | `446,175.00 SAR` | Authoritative gross payroll sum |
| **Sum of Displayed Components** | `446,675.00 SAR` | `basic_salary + housing + transport + other + overtime` |
| **Unreconciled Component Difference** | `-500.00 SAR` | Gross payroll minus displayed components (Sarah Jenkins anomaly) |
| **Net Payroll** | `437,475.00 SAR` | Net salary disbursed to paid employees |
| **Gross minus Deductions** | `437,475.00 SAR` | Gross payroll total minus total deductions |
| **Net Unreconciled Difference** | `0.00 SAR` | Net payroll minus (Gross minus deductions) |
| **Project Payroll Total** | `446,175.00 SAR` | Sum of project cost distributions |
| **Department Payroll Total** | `446,175.00 SAR` | Sum of department cost distributions |
| **Employees Paid Count** | `20` | Unique paid employee count |
| **Payroll Exception Count** | `15` | Exceptions registered in `mart_payroll_exceptions` |

---

## 4. Visual Screenshot Details
- **Dashboard Screenshot Path**: `docs/qa/screenshots/milestone_2b_payroll_dashboard.png`

---

## 5. Files Changed
- `scripts/build_warehouse.py` (added reconciliation views, validation checks, exception components)
- `backend/app/schemas/payroll.py` (Pydantic schema definitions)
- `backend/app/api/payroll.py` (added endpoints and reconciliation logic)
- `frontend/src/lib/types.ts` (added typescript interfaces)
- `frontend/src/lib/api.ts` (integrated API fetch functions)
- `frontend/src/pages/Payroll.tsx` (implemented 6-row ECharts and reconciliation layout)
- `frontend/src/components/layout/SidebarNavigation.tsx` (enabled Payroll route)
- `config/metrics_dictionary.yml` (documented metrics and variance thresholds)
- `docs/DATA_MODEL.md` (documented new DuckDB views)
- `docs/METRICS_DICTIONARY.md` (documented payroll formulas)
- `docs/DEVELOPMENT_LOG.md` (logged milestone 2b entries)
- `docs/DECISIONS.md` (logged architectural decisions)

---

## 6. Known Limitations
1. **Unexcused Overtime**: Overtime costs are calculated directly from payroll ledger records. They do not cross-reference attendance logs to enforce approval limits on the front end, though anomalies are flagged in the exceptions table.
2. **MoM Trend Anchor**: The trends currently look up to three fixed months of historical CSV data. In production, this will query historical partitions dynamically.

---

## 7. Data Integrity Confirmation
> [!IMPORTANT]
> Antigravity confirms that no real HR data or employee records were used. All inputs, calculations, and tests are built on synthetic, randomized sample data profiles.
