# Milestone 3K - Validation Rule Dictionary

| Rule | Validation |
|------|------------|
| Required fields | All schema-defined fields must be present |
| Evidence ID | Must be AUTH-EVD-001, AUTH-EVD-002, or AUTH-EVD-003 |
| Signatory role | Must be CHRO, CISO, or IT Operations Director |
| Evidence status | Must be an allowed schema status |
| Evidence source | Must be Synthetic Only |
| Source category | Must be Data Quality / Command Center Metadata |
| Decision recommendation | Must remain Hold |
| Real-data execution | Must remain Not Approved |
| Load scheduling | Must remain Not Approved |
| Stop criteria count | Must equal 22 |
| Restricted fields | Must not include rejected field names |

Synthetic validation failures reject the synthetic evidence file only. They do not change real authorization state.
