# Encrypted Storage Requirements

This document outlines the security controls and technical requirements for any future storage of real data in the HR Command Center.

---

## 1. Directory and Disk Encryption
*   **AES-256 Encryption**: Staging folders under `data/real_*` must reside on disk partitions encrypted using AES-256.
*   **Git Exclusions**: Confirmed that all CSV, Excel, and DB files in these directories are git-ignored.
*   **File Permissions**: Folder permissions must restrict read/write access strictly to the system service account and systems architect.

---

## 2. Retention and Deletion Enforcement
*   **Raw Files Purge**: Raw inbound spreadsheets are kept for a maximum of 90 days in `data/real_archive/` before being deleted by an automated cron utility.
*   **Quarantine Isolation**: Rejected files are deleted after 30 days. No manual backups may bypass these timelines.
