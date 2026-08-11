"""Category F: period-level fabrication.

The proofs this file exists for, in the order they matter:

  1. a working day INSIDE declared coverage with no attendance row is still
     an absence. This is the test that stops the fix quietly becoming a
     suppression of real signal.
  2. a working day OUTSIDE declared coverage is NULL - not 1.0 (a fabricated
     absence, and in KSA absence feeds Article 80 and payroll deduction) and
     not 0.0 (a fabricated presence, which is silent and inflates compliance).
  3. attendance_compliance_pct divides by MEASURED days.
  4. declared-but-not-covered, rows-outside-coverage and declared-but-
     unsupported all fail loudly.
  5. ruling 2: a trend month before the declared history depth is NULL.

1-3 and 5 run the REAL model SQL against a fixture, with jinja rendered by
substitution, so they cannot pass while the shipped SQL says something else.

Synthetic only. No warehouse, no client data.
"""
import datetime
import os
import re
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

import onboarding as onb  # noqa: E402

MODELS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")


def render(model, variables, refs=None):
    """The shipped model SQL, with jinja resolved by substitution."""
    with open(os.path.join(MODELS, model + ".sql"), encoding="utf-8") as handle:
        sql = handle.read()
    sql = re.sub(r"\{\{\s*config\([^)]*\)\s*\}\}", "", sql)
    sql = re.sub(r"\{\{\s*ref\(\s*'([a-z0-9_]+)'\s*\)\s*\}\}",
                 lambda m: (refs or {}).get(m.group(1), m.group(1)), sql)

    def _var(match):
        name = match.group(1)
        if name not in variables:
            raise AssertionError("model {} reads an unset var: {}".format(model, name))
        return str(variables[name])

    sql = re.sub(r"\{\{\s*var\(\s*'([a-z0-9_]+)'\s*\)\s*\}\}", _var, sql)
    assert "{{" not in sql, "unrendered jinja in {}:\n{}".format(model, sql[:400])
    return sql


VARS = {
    "start_date_str": "2026-08-01",
    "end_date_str": "2026-08-31",
    "attendance_coverage_start": "2026-08-01",
    "attendance_coverage_end": "2026-08-07",
    "weekend_days_sql": "'Friday'",
    "report_month": "2026-08",
    "trend_m1": "2026-06", "trend_m1_end": "2026-06-30",
    "trend_m2": "2026-07", "trend_m2_end": "2026-07-31",
    "employees_history_since": "1900-01-01",
}


@pytest.fixture
def conn():
    connection = duckdb.connect(":memory:")
    connection.execute("""
        CREATE TABLE employees_fixture AS
        SELECT * FROM (VALUES
            ('E1', 'Alpha', 'Ops', 'P1', 'Active', DATE '2020-01-01', CAST(NULL AS DATE))
        ) AS t(employee_id, employee_name, department, project, status,
               joining_date, termination_date);
    """)
    # one real attendance row, on a covered working day
    connection.execute("""
        CREATE TABLE attendance_fixture AS
        SELECT * FROM (VALUES
            ('E1', DATE '2026-08-03', CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP),
             TIMESTAMP '2026-08-03 08:00:00', TIMESTAMP '2026-08-03 17:00:00',
             0, 0, 0, 0, 0.0, TRUE, 0.0, 'Known')
        ) AS t(employee_id, attendance_date, scheduled_start, scheduled_end,
               actual_check_in, actual_check_out, calculated_late_minutes,
               calculated_net_late_minutes, excused_late_minutes,
               missing_punch_count, overtime_hours, overtime_approved,
               absence_days, record_classification);
    """)
    yield connection
    connection.close()


def expected(conn, **overrides):
    variables = dict(VARS, **overrides)
    sql = render("base_expected_attendance", variables, refs={
        "base_employees_deduplicated": "employees_fixture",
        "base_attendance_current": "attendance_fixture",
    })
    conn.execute("CREATE OR REPLACE VIEW base_expected_attendance AS " + sql)
    return conn


# --------------------------------------------------------------------------
# proof 1 - absence detection still works inside declared coverage
# --------------------------------------------------------------------------

def test_a_covered_working_day_with_no_row_is_still_an_absence(conn):
    """The fix must NOT weaken absence detection. Coverage is what makes the
    inference valid, not what removes it."""
    expected(conn)
    rows = conn.execute("""
        SELECT calendar_date, absence_days, coverage_status
        FROM base_expected_attendance
        WHERE coverage_status = 'covered' AND attendance_date IS NULL
        ORDER BY calendar_date
    """).fetchall()
    assert rows, "no covered working day without a row - fixture is wrong"
    assert all(r[1] == 1.0 for r in rows), rows
    # Friday is the only weekend day in the rules, so 08-01 (a Saturday)
    # onwards are all working days. Coverage is 08-01..08-07, of which 08-07 is
    # a Friday, leaving six covered working days; 08-03 carries the real row.
    assert [str(r[0]) for r in rows] == [
        "2026-08-01", "2026-08-02", "2026-08-04", "2026-08-05", "2026-08-06"]


def test_the_day_with_a_real_row_takes_its_value(conn):
    expected(conn)
    value = conn.execute("""
        SELECT absence_days FROM base_expected_attendance
        WHERE calendar_date = DATE '2026-08-03'
    """).fetchone()[0]
    assert value == 0.0


# --------------------------------------------------------------------------
# proof 2 - outside declared coverage is NULL
# --------------------------------------------------------------------------

def test_a_working_day_outside_declared_coverage_is_null(conn):
    expected(conn)
    rows = conn.execute("""
        SELECT absence_days FROM base_expected_attendance
        WHERE coverage_status = 'not_reported'
    """).fetchall()
    assert rows, "no uncovered days - fixture is wrong"
    assert all(r[0] is None for r in rows), \
        "an uncovered day is neither absent (1.0) nor present (0.0)"


def test_the_uncovered_rows_still_exist_so_the_gap_is_countable(conn):
    """NULL is not the same as no row. Narrowing the calendar would show a
    shorter month with no indication anything was missing."""
    expected(conn)
    covered, not_reported = conn.execute("""
        SELECT COUNT(*) FILTER (WHERE coverage_status = 'covered'),
               COUNT(*) FILTER (WHERE coverage_status = 'not_reported')
        FROM base_expected_attendance
    """).fetchone()
    assert covered == 6 and not_reported == 21
    assert covered + not_reported == 27, "August 2026 has 27 non-Friday days"


def test_the_whole_period_uncovered_produces_no_absences_at_all(conn):
    """The 494/513 case: attendance declared but no day reported on."""
    expected(conn, attendance_coverage_start="2026-09-01",
             attendance_coverage_end="2026-09-30")
    total, absences = conn.execute("""
        SELECT COUNT(*), COUNT(absence_days) FROM base_expected_attendance
    """).fetchone()
    assert total == 27, "the rows still exist"
    assert absences == 0, "and not one of them claims an absence"


# --------------------------------------------------------------------------
# proof 3 - the compliance denominator is measured days
# --------------------------------------------------------------------------

def test_compliance_divides_by_measured_days_not_every_working_day(conn):
    expected(conn)
    conn.execute("CREATE OR REPLACE VIEW base_attendance_payroll_overtime AS "
                 "SELECT 0.0 AS payroll_ot_cost WHERE FALSE")
    conn.execute("CREATE OR REPLACE VIEW mart_attendance_exceptions AS "
                 "SELECT 1 WHERE FALSE")
    sql = render("mart_attendance_kpis", VARS, refs={
        "base_expected_attendance": "base_expected_attendance",
        "base_attendance_payroll_overtime": "base_attendance_payroll_overtime",
        "mart_attendance_exceptions": "mart_attendance_exceptions",
    })
    pct, absence = conn.execute(
        "SELECT attendance_compliance_pct, absence_days FROM ({})".format(sql)
    ).fetchone()
    # 6 measured days, 5 of them absences -> 1 - 5/6
    assert absence == 5.0
    assert pct == pytest.approx(1 - 5 / 6), (
        "dividing by all 27 working days would give ~0.815 - the unreported "
        "days would inflate compliance")


def test_no_measured_days_gives_null_compliance_not_one(conn):
    """'100% compliant' over nothing is a fabricated-favourable value."""
    expected(conn, attendance_coverage_start="2026-09-01",
             attendance_coverage_end="2026-09-30")
    conn.execute("CREATE OR REPLACE VIEW base_attendance_payroll_overtime AS "
                 "SELECT 0.0 AS payroll_ot_cost WHERE FALSE")
    conn.execute("CREATE OR REPLACE VIEW mart_attendance_exceptions AS "
                 "SELECT 1 WHERE FALSE")
    sql = render("mart_attendance_kpis", VARS, refs={
        "base_expected_attendance": "base_expected_attendance",
        "base_attendance_payroll_overtime": "base_attendance_payroll_overtime",
        "mart_attendance_exceptions": "mart_attendance_exceptions",
    })
    pct, absence = conn.execute(
        "SELECT attendance_compliance_pct, absence_days FROM ({})".format(sql)
    ).fetchone()
    assert pct is None
    assert absence is None, "a COALESCE here would restore a fabricated zero"


def test_the_absence_total_is_not_coalesced_back_to_zero():
    """Guard the guard: the COALESCE is one 'fix a null' away from returning."""
    with open(os.path.join(MODELS, "mart_attendance_kpis.sql"), encoding="utf-8") as f:
        sql = f.read()
    assert "COALESCE(SUM(absence_days)" not in sql
    assert "COUNT(absence_days)" in sql


def test_every_exception_branch_is_confined_to_covered_days():
    """15 branches, one predicate each - mechanical, and mechanical at that
    scale is where one gets missed."""
    with open(os.path.join(MODELS, "mart_attendance_exceptions.sql"),
              encoding="utf-8") as f:
        sql = f.read()
    reads = len(re.findall(r"FROM \{\{ ref\('base_expected_attendance'\) \}\}", sql))
    guards = sql.count("coverage_status = 'covered'")
    print("\n[category-f] exception branches reading the calendar: {} | "
          "guarded: {}".format(reads, guards))
    assert reads == guards == 7


# --------------------------------------------------------------------------
# proof 5 - ruling 2 as amended: history depth
# --------------------------------------------------------------------------

def _headcount_trend(conn, history_since):
    conn.execute("CREATE OR REPLACE VIEW stg_employees AS "
                 "SELECT * FROM employees_fixture")
    conn.execute("CREATE OR REPLACE VIEW base_active_workforce AS "
                 "SELECT * FROM employees_fixture")
    sql = render("mart_workforce_headcount_trend",
                 dict(VARS, employees_history_since=history_since),
                 refs={"stg_employees": "stg_employees",
                       "base_active_workforce": "base_active_workforce"})
    return dict(conn.execute(sql).fetchall())


def test_history_before_the_declared_depth_is_null_not_a_derived_figure(conn):
    trend = _headcount_trend(conn, "2026-07-01")
    assert trend["2026-06"] is None, (
        "a month the file cannot speak to must be null, not an understated "
        "headcount that renders as smooth growth")
    assert trend["2026-07"] == 1
    assert trend["2026-08"] == 1


def test_a_declared_depth_that_covers_the_window_derives_normally(conn):
    trend = _headcount_trend(conn, "2020-01-01")
    assert trend == {"2026-06": 1, "2026-07": 1, "2026-08": 1}


def test_no_declared_depth_resolves_to_the_period_start(conn):
    """build_warehouse falls back to report_month_start in real mode, so every
    historical month is null until a depth is declared."""
    trend = _headcount_trend(conn, "2026-08-01")
    assert trend["2026-06"] is None and trend["2026-07"] is None
    assert trend["2026-08"] == 1


def test_the_exec_trend_payroll_axis_is_not_coalesced():
    with open(os.path.join(MODELS, "mart_exec_trends.sql"), encoding="utf-8") as f:
        sql = f.read()
    assert "COALESCE(pm.payroll_cost" not in sql, (
        "ruling 1: a month with no payroll is null, never a chart saying the "
        "client paid nobody")


# --------------------------------------------------------------------------
# proof 4 - the loud failures
# --------------------------------------------------------------------------

@pytest.fixture
def registry(tmp_path, monkeypatch):
    path = tmp_path / "declared_domains.yml"
    monkeypatch.setattr(onb, "REGISTRY_PATH", str(path))
    monkeypatch.setattr(onb, "CONTAINER_REGISTRY_PATH", str(path))
    return path


def test_declared_but_not_covered_fails_loudly(registry):
    registry.write_text("version: 2\ndeclared:\n  - attendance\n", encoding="utf-8")
    with pytest.raises(onb.OnboardingError) as excinfo:
        onb.assert_coverage_declared({"attendance"})
    message = str(excinfo.value)
    assert "attendance" in message and "coverage" in message
    assert "YYYY-MM-DD" in message
    assert "فترة تغطية" in message


def test_a_period_grained_domain_needs_no_coverage(registry):
    registry.write_text("version: 2\ndeclared:\n  - payroll\n", encoding="utf-8")
    assert onb.assert_coverage_declared({"payroll", "employees"}) is True


def test_coverage_is_read_from_the_registry_not_inferred(registry):
    registry.write_text(
        "version: 2\ndeclared:\n  - attendance\ncoverage:\n"
        "  attendance:\n    start: 2026-08-01\n    end: 2026-08-14\n",
        encoding="utf-8")
    assert onb.load_coverage() == {
        "attendance": (datetime.date(2026, 8, 1), datetime.date(2026, 8, 14))}
    assert onb.assert_coverage_declared({"attendance"}) is True


def test_a_backwards_window_is_rejected(registry):
    registry.write_text(
        "version: 2\ncoverage:\n  attendance:\n"
        "    start: 2026-08-14\n    end: 2026-08-01\n", encoding="utf-8")
    with pytest.raises(onb.OnboardingError):
        onb.load_coverage()


def test_rows_outside_declared_coverage_are_rejected(tmp_path, registry):
    import polars as pl

    import ingest_raw

    path = tmp_path / "attendance.csv"
    pl.DataFrame({"employee_id": ["E1", "E2"],
                  "attendance_date": ["2026-08-03", "2026-08-20"]}).write_csv(path)
    coverage = {"attendance": (datetime.date(2026, 8, 1), datetime.date(2026, 8, 14))}
    with pytest.raises(onb.OnboardingError) as excinfo:
        ingest_raw.check_rows_within_declared_coverage(
            "attendance", str(path), coverage=coverage)
    assert "2026-08-20" in str(excinfo.value)


def test_rows_inside_declared_coverage_pass(tmp_path, registry):
    import polars as pl

    import ingest_raw

    path = tmp_path / "attendance.csv"
    pl.DataFrame({"employee_id": ["E1"],
                  "attendance_date": ["2026-08-03"]}).write_csv(path)
    coverage = {"attendance": (datetime.date(2026, 8, 1), datetime.date(2026, 8, 14))}
    assert ingest_raw.check_rows_within_declared_coverage(
        "attendance", str(path), coverage=coverage) == coverage["attendance"]


def test_declared_history_deeper_than_the_file_fails_loudly(registry):
    with pytest.raises(onb.OnboardingError) as excinfo:
        onb.assert_history_supported(
            "employees", datetime.date(2026, 1, 1),
            declared_since=datetime.date(2025, 1, 1))
    message = str(excinfo.value)
    assert "2025-01-01" in message and "2026-01-01" in message


def test_a_file_reaching_further_back_than_declared_is_fine(registry):
    assert onb.assert_history_supported(
        "employees", datetime.date(2019, 1, 1),
        declared_since=datetime.date(2025, 1, 1)) == datetime.date(2025, 1, 1)


def test_declare_writes_coverage_and_history(registry):
    onb.declare("attendance", coverage_start="2026-08-01",
                coverage_end="2026-08-14",
                contracted={"attendance", "employees"})
    onb.declare("employees", history_since="2024-01-01",
                contracted={"attendance", "employees"})
    assert onb.load_coverage()["attendance"] == (
        datetime.date(2026, 8, 1), datetime.date(2026, 8, 14))
    assert onb.load_history_depth()["employees"] == datetime.date(2024, 1, 1)


def test_a_v1_registry_still_loads(registry):
    """No value in breaking an existing declaration to add two optional keys."""
    registry.write_text("version: 1\ndeclared:\n  - employees\n", encoding="utf-8")
    assert onb.load_declared(contracted={"employees"}) == {"employees"}
    assert onb.load_coverage() == {}
    assert onb.load_history_depth() == {}
