# Data Retention and Deletion Policy

This policy outlines the storage duration, archiving methods, and deletion triggers for all data processed by the HR Analytics Command Center.

---

## 1. Data Retention Matrix

| Data Category | Retention Period | Storage Location | Deletion Trigger | Archive Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Inbound Files** | 90 Days | `data/real_archive/` | Automated cron job | Move to secure offline storage |
| **Quarantine Files** | 30 Days | `data/real_quarantine/` | Automated cron job | Permanent purge (no archive) |
| **Approved Synthetic Files**| 365 Days | `data/synthetic/` | Manual review | Git repository version history |
| **Transformed Tables** | 5 Years | DuckDB database | Automated purge | Database snapshot backup |
| **Dashboard Marts** | 5 Years | DuckDB database | Automated purge | Database snapshot backup |
| **QA Reports** | 365 Days | `docs/qa/reports/` | Manual review | PDF backup vault |
| **Audit Logs** | 365 Days | Secure Syslog server | Automated purge | Immutable write-once log archive |

---

## 2. Legal Holds and Exceptions
*   **Active Investigations**: Data subject to open labor disputes, active employee relations cases, or audit inquiries is exempt from automatic deletion.
*   **Authorization**: Deletion overrides require the joint written approval of the HR VP and Chief Legal Counsel.

---

## 3. Real Data Load Purge Triggers
During pilot loading, any detected masking failures, schema overrides, or unauthorized raw field exposures will trigger an immediate database sector purge and snapshot roll back.
