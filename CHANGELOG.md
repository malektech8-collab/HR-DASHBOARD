# Changelog

All notable changes to this project are documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Per the versioning policy in [DOCUMENTATION.md §17](DOCUMENTATION.md#17-versioning--release-policy), `production` and the `v1.0.0` tag stay frozen — entries under **Unreleased** describe commits on `main` that have not yet been folded into a new tagged release.

## [Unreleased]

### Fixed
- Sidebar footer showed a stale internal milestone label (`Version 1.0.0 (Milestone 2H)`) instead of the official release name; now reads `Version 1.0.0 "Genesis"`. ([`6425c35`](../../commit/6425c35))
- Several dbt marts contained leftover Python f-string-style placeholders (e.g. `{rec_report_month}`, `{talent_report_month}`) never converted to dbt's `{{ var(...) }}` templating. Two of these sat in `WHERE` clauses, so the literal placeholder text never matched the real period and silently returned zero rows: `base_workforce_plan_current` and `base_performance_reviews_current`. This cascaded into empty widgets on the Talent & Succession page (performance distribution, by-department, by-project, flight-risk) and the Recruitment & Hiring page (Workforce Plan vs. Actual). The remaining occurrences were display-only columns showing the literal placeholder text instead of the period (e.g. `"2026-06"`) in trend charts. ([`6be5057`](../../commit/6be5057))
- `mart_exec_kpis`, `mart_exec_trends`, and `mart_workforce_headcount_trend` hardcoded `'2026-06'`/`'2026-04'`/`'2026-05'` literals instead of using the `report_month` dbt vars — correct only by coincidence for the current report period, and would silently go stale if the period ever changed. Now parameterized like the rest of the project. ([`6be5057`](../../commit/6be5057))
- Local warehouse data: `data/silver/employees.parquet.uploaded` was a leftover marker from an earlier manual test of the CSV-upload feature. The ingestion pipeline treats any `.uploaded` marker as "protect this table forever," so a bad test upload with malformed/missing `joining_date` values was frozen in place indefinitely, zeroing out the entire attendance-calendar base table (`base_expected_attendance`) and the four Attendance-page breakdown widgets (by-department, by-project, late arrival, missing punches). Removed the stale marker and re-ran the pipeline to regenerate correct data. Not a code change — local runtime state only, not tracked in git.
