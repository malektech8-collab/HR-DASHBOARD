# Milestone 3A — Privacy and Compliance Review

## 1. Objectives & Scope
This review assesses the adequacy of the proposed privacy controls, masking specifications, and role-based access rules defined in Milestone 3A to ensure compliance with the KSA Personal Data Protection Law (PDPL) and NDMO regulations.

No real data was accessed, and no live connections were established.

---

## 2. Review of Masking & Redaction Specifications

### 2.1 Employee Name Pseudonymization
- **Specification**: In general dashboards, the name is hashed or represented as `Initials + Employee ID` (e.g. `K.A. (EMP-0019)`).
- **Assessment**: **PASSED**. This pseudonymization strategy prevents general users from identifying individuals, while keeping data useful for operational metrics.

### 2.2 National ID & Iqama Masking
- **Specification**: Masking format leaving only the last 4 digits visible: `*****1234`.
- **Assessment**: **PASSED**. Meets standard ID truncation guidelines, preventing raw ID exposure in analytical models.

### 2.3 Salary & Allowance Aggregation
- **Specification**: Row-level salary data is restricted; general views use system-wide or department-level aggregations (SUM/AVG) with a minimum group size limit (N=5).
- **Assessment**: **PASSED**. Standard industry best practice to prevent deductive identification in small departments.

### 2.4 Bank Details & IBAN Redaction
- **Specification**: Raw IBANs are completely scrubbed at ingestion.
- **Assessment**: **PASSED**. Eliminates security risks associated with storing transactional banking credentials in analytical systems.

### 2.5 Medical & Legal Cases Redaction
- **Specification**: Medical logs are not imported. ER case descriptions undergo NLP entity redaction to scrub specific names and financial amounts.
- **Assessment**: **PASSED**. Minimizes risks related to Sensitive Personal Data handling.

---

## 3. Review of Role-Based Access Control (RBAC)
The 11 system roles established in `access_roles.yml` offer clear segmentations:
- Core operations, financial (payroll), and employee relations (legal) modules have separate, non-overlapping management roles.
- Aggregate-only roles (e.g. `viewer_executive_aggregate_only`) ensure executive viewers cannot drill down to individual records.
- Auditors are read-only with no refresh or system update capabilities.

**Conclusion**: The RBAC schema meets the principle of least privilege.
