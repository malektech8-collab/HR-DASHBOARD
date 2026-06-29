# HR Command Center — Privacy & Sensitive Data Masking Policy

## 1. Regulatory Context & Compliance
This policy defines the governance and technical implementation constraints to ensure compliance with the National Data Management Office (NDMO) and Personal Data Protection Law (PDPL) requirements in the Kingdom of Saudi Arabia.

---

## 2. Field Classification Taxonomy
All data ingested into the HR Command Center database is classified under one of the following privacy levels:

- **Public**: Broad public consumption. (None in this system)
- **Internal**: Shared within the enterprise network (e.g. `employee_id`, `department`, `project`).
- **Confidential**: Business-sensitive (e.g. `performance_rating`, `successor_readiness`, `flight_risk`).
- **Personal Data**: Identifiable employee traits (e.g. `employee_name`, `email`, `phone_number`).
- **Sensitive Personal Data**: High-risk identifiers (e.g. `medical_insurance_policy`, `chronic_illness_flags`).
- **Financial Sensitive**: Payout structures (e.g. `gross_salary`, `net_salary`, `allowances`, `deductions`).
- **Legal Sensitive**: Disciplinary, workplace harassment, or labor court filings (e.g. `disciplinary_cases_description`).
- **Government ID Sensitive**: Official identities (e.g. `national_id_number`, `passport_number`).

---

## 3. Masking & Redaction Rules

### Employee Name
- **Standard dashboards**: Masked to initials and ID: e.g. `K.A. (EMP-0019)`.
- **System views**: Available only to users assigned `hr_executive` or `hr_operations_manager` roles.

### National ID / Iqama & Passport Numbers
- **Standard dashboards**: Must be partially masked: e.g. `1098******` (retains last 4 digits).
- **System views**: Fully masked in all frontend dashboard components by default.

### Salary & Allowances
- **Executive views**: Total payroll costs are aggregated (e.g. SUM at department/project level).
- **Row-level views**: Restricted to roles: `payroll_manager` and `hr_executive`. All other roles receive masked value strings.

### Bank Account & IBAN
- **System policy**: Completely redacted at ingestion: replacement string `[REDACTED_FINANCIAL_DETAIL]`. IBAN details are never kept in the analytical DuckDB database.

### Medical / Health Fields
- **System policy**: Aggregated to corporate insurance premium calculations only. Personal medical logs or chronic disease profiles are strictly prohibited from ingestion.

### ER Case Details & Disciplinary Descriptions
- **System policy**: Descriptions are processed using NLP text-redaction to scrub names and financial figures, or hidden completely from non-authorized roles.

### Performance Ratings & Succession
- **Standard dashboards**: Aggregated performance metrics only. Individual row-level ratings are restricted to `talent_manager` and `hr_executive` roles.
- **Successor Employee Key**: Hashed deterministically using opaque tokens (e.g., `SUCC-0001`). Displaying raw employee IDs, names, or initials is prohibited. Dashboards remain aggregate-only.

---

## 4. Real Data Auditing
During controlled load cycles, the system runs post-load validation scripts to audit that 100% of PII and salary fields match the masking rules defined above.
