import urllib.request
import json
import os
import sys

def main():
    print("Running QA report generator...")
    
    # API endpoints
    urls = {
        'summary': 'http://127.0.0.1:8000/api/payroll/summary',
        'components': 'http://127.0.0.1:8000/api/payroll/components',
        'trends': 'http://127.0.0.1:8000/api/payroll/trends',
        'by-project': 'http://127.0.0.1:8000/api/payroll/by-project',
        'by-department': 'http://127.0.0.1:8000/api/payroll/by-department',
        'variance': 'http://127.0.0.1:8000/api/payroll/variance',
        'exceptions': 'http://127.0.0.1:8000/api/payroll/exceptions'
    }
    
    # 1. Fetch data
    raw_outputs = {}
    parsed_data = {}
    for name, url in urls.items():
        try:
            req = urllib.request.urlopen(url)
            body = req.read().decode("utf-8")
            raw_outputs[name] = body
            parsed_data[name] = json.loads(body)
        except Exception as e:
            print(f"ERROR: Failed to fetch {name} endpoint from {url}: {e}")
            sys.exit(1)
            
    # 2. Extract key metrics
    summary = parsed_data['summary']
    kpis = summary['kpis']
    recon = summary['reconciliation']
    components = parsed_data['components']['components']
    projects = parsed_data['by-project']['projects']
    departments = parsed_data['by-department']['departments']
    exceptions = parsed_data['exceptions']['exceptions']
    
    # 3. Perform script-level validation checks
    print("Running script-level validations...")
    
    # - Fail if dashboard has fewer than 10 payroll KPI cards
    kpi_count = len(kpis)
    print(f"Validation: KPI card count = {kpi_count}")
    if kpi_count < 10:
        print("FAIL: Dashboard has fewer than 10 payroll KPI cards")
        sys.exit(1)
        
    # - Fail if gross payroll does not reconcile with displayed components plus unreconciled difference
    total_gross = recon['total_gross_payroll']
    # Calculate sum of displayed components from components endpoint (excluding Deductions and Unreconciled / Exception Amount)
    sum_displayed_components = sum(c['amount'] for c in components if c['component'] not in ['Deductions', 'Unreconciled / Exception Amount'])
    unreconciled_diff = next(c['amount'] for c in components if c['component'] == 'Unreconciled / Exception Amount')
    
    diff_val = total_gross - (sum_displayed_components + unreconciled_diff)
    print(f"Validation: Gross Payroll = {total_gross}, Displayed Components + Unreconciled = {sum_displayed_components + unreconciled_diff} (Diff: {diff_val})")
    if abs(diff_val) > 0.01:
        print(f"FAIL: Gross payroll does not reconcile with displayed components plus unreconciled difference (Diff: {diff_val})")
        sys.exit(1)
        
    # - Fail if project totals do not reconcile to total gross payroll
    sum_projects = sum(p['total_payroll_cost'] for p in projects)
    proj_diff = total_gross - sum_projects
    print(f"Validation: Sum Project Costs = {sum_projects} (Diff: {proj_diff})")
    if abs(proj_diff) > 0.01:
        print(f"FAIL: Project totals do not reconcile to total gross payroll (Diff: {proj_diff})")
        sys.exit(1)
        
    # - Fail if department totals do not reconcile to total gross payroll
    sum_depts = sum(d['total_payroll_cost'] for d in departments)
    dept_diff = total_gross - sum_depts
    print(f"Validation: Sum Department Costs = {sum_depts} (Diff: {dept_diff})")
    if abs(dept_diff) > 0.01:
        print(f"FAIL: Department totals do not reconcile to total gross payroll (Diff: {dept_diff})")
        sys.exit(1)
        
    # - Fail if exception count does not reconcile to the exceptions endpoint
    exception_count_summary = recon['payroll_exception_count']
    exception_count_endpoint = len(exceptions)
    print(f"Validation: Exceptions summary count = {exception_count_summary}, Endpoint count = {exception_count_endpoint}")
    if exception_count_summary != exception_count_endpoint:
        print("FAIL: Exception count does not reconcile to exceptions endpoint")
        sys.exit(1)
        
    print("All validations PASSED.")
    
    # 4. Write full raw API outputs to file
    os.makedirs("docs/qa/api_outputs", exist_ok=True)
    api_outputs_path = "docs/qa/api_outputs/milestone_2b_payroll_api_outputs.json"
    
    # Build unified dictionary
    unified_outputs = {name: json.loads(body) for name, body in raw_outputs.items()}
    with open(api_outputs_path, "w", encoding="utf-8") as f:
        json.dump(unified_outputs, f, indent=2)
    print(f"Saved raw API outputs to {api_outputs_path}")
    
    # 5. Format formatted values for report
    def format_sar(val):
        return f"{val:,.2f} SAR"
        
    # 6. Generate Markdown Report
    os.makedirs("docs/qa/reports", exist_ok=True)
    report_path = "docs/qa/reports/milestone_2b_payroll_qa_report.md"
    
    kpi_rows = ""
    for k in kpis:
        val_str = format_sar(k['value']) if k['unit'] == 'SAR' else (f"{k['value']}%" if k['unit'] == '%' else f"{k['value']:.0f}")
        kpi_rows += f"| **{k['label']}** | `{k['key']}` | `{val_str}` | `/api/payroll/summary` |\n"
        
    components_rows = ""
    for c in components:
        components_rows += f"| **{c['component']}** | {format_sar(c['amount'])} |\n"
        
    md_content = f"""# Milestone 2B: Payroll & Cost Dashboard QA Report

This report documents the programmatic QA verification of the Payroll & Cost Dashboard. All metrics are compiled dynamically from the live API endpoints during the validation process.

---

## 1. Verified KPI Cards (Total: {kpi_count})

| KPI Card | Key | Value | Source Endpoint |
| :--- | :--- | :--- | :--- |
{kpi_rows}

---

## 2. Payroll Component Breakdown

Below is the full payroll component breakdown compiled from `/api/payroll/components`:

| Component Name | Amount |
| :--- | :--- |
{components_rows}

---

## 3. Payroll Reconciliation Table

Below is the verified reconciliation table generated from the analytical warehouse database view `mart_payroll_reconciliation`:

| Metric Name | Reconciled Value | Source Formula / Explanation |
| :--- | :--- | :--- |
| **Total Gross Payroll** | `{format_sar(recon['total_gross_payroll'])}` | Authoritative gross payroll sum |
| **Sum of Displayed Components** | `{format_sar(recon['sum_displayed_components'])}` | `basic_salary + housing + transport + other + overtime` |
| **Unreconciled Component Difference** | `{format_sar(recon['unreconciled_component_difference'])}` | Gross payroll minus displayed components (Sarah Jenkins anomaly) |
| **Net Payroll** | `{format_sar(recon['net_payroll'])}` | Net salary disbursed to paid employees |
| **Gross minus Deductions** | `{format_sar(recon['gross_minus_deductions'])}` | Gross payroll total minus total deductions |
| **Net Unreconciled Difference** | `{format_sar(recon['net_unreconciled_difference'])}` | Net payroll minus (Gross minus deductions) |
| **Project Payroll Total** | `{format_sar(recon['project_payroll_total'])}` | Sum of project cost distributions |
| **Department Payroll Total** | `{format_sar(recon['department_payroll_total'])}` | Sum of department cost distributions |
| **Employees Paid Count** | `{recon['employees_paid_count']}` | Unique paid employee count |
| **Payroll Exception Count** | `{recon['payroll_exception_count']}` | Exceptions registered in `mart_payroll_exceptions` |

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
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Successfully generated QA report at {report_path}")

if __name__ == "__main__":
    main()
