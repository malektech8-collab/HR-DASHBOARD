# Gate 3 Privacy Review Protocol

This protocol outlines the validation rules and audits required to ensure compliance with the Saudi Personal Data Protection Law (PDPL).

---

## 1. Compliance Checklist

All data flows must satisfy the following criteria:

*   **Principle of Minimization**: Raw file columns that are not mapped to target canonical fields (such as bank details or IBAN numbers) must be fully redacted during ingestion.
*   **Privacy Class Mapping**: Every field in `source_mapping_validation.yml` must reference an NDMO classification level.
*   **Access Limitations**: Standard users must not access raw identifying employee rows. Individual personnel files require authorized roles.
*   **Explicit Masking Rules**: Masking methods (redaction, pseudonymization, hashing) must be declared and verified in sandbox views.
*   **Opaque Successor Hashing**: Identifiers for succession candidates must utilize deterministic tokens only. Names, initials, or numbers are prohibited.
