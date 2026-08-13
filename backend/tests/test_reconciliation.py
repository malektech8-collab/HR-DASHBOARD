# -*- coding: utf-8 -*-
"""Every reconciliation check, watched failing before it is trusted to pass.

THE RULE THIS FILE ENFORCES, which is now a standing practice:

    A verification line earns its place only once someone has confirmed it can
    fail.

Two cycles produced two instances of the same class. `npx tsc --noEmit`
typechecked ZERO files, because tsconfig.json is a solution file with
`"files": []`. The reconciliation suite compared the Command Center overview
against the marts it had just been copied from, so eight of its eleven checks
could not fail. Both were quoted as evidence for many cycles and accepted at
review each time.

So each check below gets two tests: it passes on correct data, and it FAILS on
tampered data. A check that only ever passes is indistinguishable from a check
that cannot fail, and this project has now shipped two of the latter.
"""
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import reconciliation  # noqa: E402


# --------------------------------------------------------------------------
# a fixture warehouse: the base rows, and an overview that agrees with them
# --------------------------------------------------------------------------

SETUP = """
CREATE TABLE base_active_workforce(employee_id VARCHAR, is_saudi BOOLEAN,
                                   nationality VARCHAR);
INSERT INTO base_active_workforce VALUES
    ('E1', TRUE, 'Saudi'), ('E2', FALSE, 'Egyptian'),
    ('E3', TRUE, 'Saudi'), ('E4', NULL, '');

CREATE TABLE base_payroll_current(employee_id VARCHAR, gross_pay DOUBLE);
INSERT INTO base_payroll_current VALUES ('E1', 10000.0), ('E2', 5000.5);

CREATE TABLE base_expected_attendance(absence_days DOUBLE,
                                      calculated_net_late_minutes INTEGER,
                                      missing_punch_count INTEGER);
INSERT INTO base_expected_attendance VALUES
    (0.0, 0, 0), (0.0, 0, 0), (1.0, 0, 0), (0.0, 30, 0), (NULL, NULL, NULL);

CREATE TABLE base_er_case_population(case_id VARCHAR, case_status VARCHAR);
INSERT INTO base_er_case_population VALUES
    ('C1', 'Open'), ('C2', 'In Progress'), ('C3', 'Closed');

CREATE TABLE base_recruitment_requisitions_current(requisition_id VARCHAR,
                                                   status VARCHAR);
INSERT INTO base_recruitment_requisitions_current VALUES
    ('R1', 'Open'), ('R2', 'On Hold'), ('R3', 'Filled');

CREATE TABLE base_talent_employee_population(employee_id VARCHAR);
INSERT INTO base_talent_employee_population VALUES ('E1'), ('E2'), ('E3'), ('E4');

CREATE TABLE base_performance_reviews_current(employee_id VARCHAR);
INSERT INTO base_performance_reviews_current VALUES ('E1'), ('E1'), ('E2');
"""

EXCEPTION_ARMS = ("data_quality", "workforce", "payroll", "attendance",
                  "compliance", "er", "recruitment", "talent")

# What the base rows above independently produce.
TRUTH = {
    "active_headcount": 4,
    "payroll_cost": 15000.5,
    # 4 measured days, 2 of them bad (one absence, one late) -> 1 - 2/4
    "attendance_compliance_pct": 0.5,
    # 2 Saudi, 1 non-Saudi, 1 unknown nationality excluded from BOTH sides
    "saudization_pct": 66.67,
    "open_er_cases": 2,
    "open_requisitions": 2,
    # 2 distinct reviewed of 4 in the population
    "review_completion_pct": 50.0,
    "total_active_exceptions": 8,
}


@pytest.fixture
def conn(tmp_path):
    db = duckdb.connect(str(tmp_path / "recon.duckdb"))
    db.execute(SETUP)
    for i, arm in enumerate(EXCEPTION_ARMS):
        db.execute("CREATE TABLE base_command_exception_{}(entity_id VARCHAR)"
                   .format(arm))
        db.execute("INSERT INTO base_command_exception_{} VALUES ('X{}')"
                   .format(arm, i))

    db.execute("""
        CREATE TABLE mart_command_center_overview(
            active_headcount INTEGER, payroll_cost DOUBLE,
            attendance_compliance_pct DOUBLE, saudization_pct DOUBLE,
            open_er_cases INTEGER, open_requisitions INTEGER,
            review_completion_pct DOUBLE, total_active_exceptions INTEGER)
    """)
    db.execute("INSERT INTO mart_command_center_overview VALUES (?,?,?,?,?,?,?,?)",
               [TRUTH[c["name"]] for c in reconciliation.VALUE_CHECKS])

    for table in ("base_command_center_module_registry",
                  "mart_command_center_data_freshness",
                  "mart_command_center_navigation_status"):
        db.execute("CREATE TABLE {}(module_key VARCHAR, route_path VARCHAR)"
                   .format(table))
        db.execute("INSERT INTO {} SELECT k, '/' || k FROM (VALUES {}) t(k)"
                   .format(table, ", ".join("('{}')".format(m)
                                            for m in reconciliation.MODULES)))
    yield db
    db.close()


# --------------------------------------------------------------------------
# the suite agrees with itself before anything is tampered
# --------------------------------------------------------------------------

def test_a_correct_warehouse_passes(conn):
    assert reconciliation.run(conn) == 12


def test_the_fixture_truth_covers_every_value_check():
    """A check added without a fixture value would silently go untested."""
    assert set(TRUTH) == {c["name"] for c in reconciliation.VALUE_CHECKS}


# --------------------------------------------------------------------------
# (d) EVERY value check, watched failing
# --------------------------------------------------------------------------

@pytest.mark.parametrize("check", reconciliation.VALUE_CHECKS,
                         ids=lambda c: c["name"])
def test_every_value_check_fails_when_the_served_figure_is_wrong(conn, check):
    """Tamper what the Command Center SERVES; the check must notice.

    This is the test the old suite could not have passed: it compared the
    served value against the mart it was copied from, so moving one moved both.
    """
    name = check["name"]
    conn.execute("UPDATE mart_command_center_overview SET {} = {} + 1"
                 .format(name, name))
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert name in str(excinfo.value)


@pytest.mark.parametrize("check", reconciliation.VALUE_CHECKS,
                         ids=lambda c: c["name"])
def test_every_value_check_reads_its_independent_side(conn, check):
    """Tamper the UNDERLYING ROWS instead; the check must notice that too.

    Together with the test above this pins the property that matters: the two
    sides of each comparison come from different places. A check whose
    'independent' query secretly read the same artefact would pass the first
    test and fail this one.
    """
    served_before = conn.execute(check["served"]).fetchone()[0]
    conn.execute(TAMPER_SOURCE[check["name"]])
    served_after = conn.execute(check["served"]).fetchone()[0]
    assert served_after == served_before, (
        "tampering the base rows must not move the served figure, or the "
        "two sides are not independent")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert check["name"] in str(excinfo.value)


# One tamper per check, on the BASE side.
TAMPER_SOURCE = {
    "active_headcount":
        "INSERT INTO base_active_workforce VALUES ('E9', TRUE, 'Saudi')",
    "payroll_cost":
        "INSERT INTO base_payroll_current VALUES ('E9', 1.0)",
    "attendance_compliance_pct":
        "INSERT INTO base_expected_attendance VALUES (5.0, 0, 0)",
    "saudization_pct":
        "INSERT INTO base_active_workforce VALUES ('E9', FALSE, 'Indian')",
    "open_er_cases":
        "INSERT INTO base_er_case_population VALUES ('C9', 'Open')",
    "open_requisitions":
        "INSERT INTO base_recruitment_requisitions_current VALUES ('R9', 'Open')",
    "review_completion_pct":
        "INSERT INTO base_performance_reviews_current VALUES ('E3')",
    "total_active_exceptions":
        "INSERT INTO base_command_exception_talent VALUES ('X9')",
}


def test_a_union_arm_that_stops_contributing_is_caught(conn):
    """Why the exception check sums the eight arms instead of counting the union.

    Counting base_command_center_exception_sources would agree with itself if
    an arm silently dropped out. Summing the arms separately does not.
    """
    conn.execute("DELETE FROM base_command_exception_recruitment")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert "total_active_exceptions" in str(excinfo.value)


def test_a_null_on_one_side_only_is_a_failure_not_a_pass(conn):
    """NULL == NULL is fine; NULL vs a number is a disagreement.

    Attendance compliance is legitimately NULL when no day was measured. It
    must not become a way for a check to shrug.
    """
    conn.execute("UPDATE mart_command_center_overview "
                 "SET attendance_compliance_pct = NULL")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert "attendance_compliance_pct" in str(excinfo.value)


def test_every_disagreement_is_reported_not_just_the_first(conn):
    """A broken pipeline should not become a sequence of reruns."""
    conn.execute("UPDATE mart_command_center_overview "
                 "SET active_headcount = active_headcount + 1, "
                 "    open_er_cases = open_er_cases + 1")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    message = str(excinfo.value)
    assert "active_headcount" in message and "open_er_cases" in message


# --------------------------------------------------------------------------
# (d) the module checks, watched failing - including on the REAL defect
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table", [
    "base_command_center_module_registry",
    "mart_command_center_data_freshness",
    "mart_command_center_navigation_status",
])
def test_a_corrupted_module_key_is_caught(conn, table):
    """THE DEFECT THIS REPLACED A ROW COUNT TO CATCH.

    `'{{ ref('stg_payroll') }}' AS module_key` in three models rendered as the
    quoted relation name, so payroll, attendance and compliance carried keys
    like '"hr_analytics"."main"."stg_payroll"' and route paths to match. It
    reached backend/app/api/command_center.py and the frontend.

    The old check asserted COUNT(*) = 9 and passed throughout: all nine rows
    were present. They were just wrong.
    """
    conn.execute("""UPDATE {} SET module_key = '"hr_analytics"."main"."stg_payroll"',
                    route_path = '/\"hr_analytics\".\"main\".\"stg_payroll\"'
                    WHERE module_key = 'payroll'""".format(table))
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert "payroll" in str(excinfo.value)


@pytest.mark.parametrize("table", [
    "base_command_center_module_registry",
    "mart_command_center_data_freshness",
    "mart_command_center_navigation_status",
])
def test_a_missing_module_is_caught(conn, table):
    conn.execute("DELETE FROM {} WHERE module_key = 'talent'".format(table))
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert "talent" in str(excinfo.value)


def test_a_route_that_does_not_match_its_key_is_caught(conn):
    conn.execute("UPDATE base_command_center_module_registry "
                 "SET route_path = '/payrol' WHERE module_key = 'payroll'")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    assert "route" in str(excinfo.value).lower()


def test_an_extra_module_is_caught(conn):
    """A row count of 9 would pass this if a module were also deleted."""
    conn.execute("DELETE FROM base_command_center_module_registry "
                 "WHERE module_key = 'talent'")
    conn.execute("INSERT INTO base_command_center_module_registry "
                 "VALUES ('tallent', '/tallent')")
    with pytest.raises(reconciliation.ReconciliationError) as excinfo:
        reconciliation.run(conn)
    message = str(excinfo.value)
    assert "tallent" in message and "talent" in message


# --------------------------------------------------------------------------
# no check may be quietly dropped
# --------------------------------------------------------------------------

def test_the_check_count_is_pinned():
    """8 value checks + 3 module-key checks + 1 route check.

    Pinned so that deleting a check is a deliberate edit to this number rather
    than a quiet reduction in coverage - which is how eight tautologies came to
    be counted as eleven checks in the first place.
    """
    assert len(reconciliation.VALUE_CHECKS) == 8
    assert len(reconciliation.REGISTRY_CHECKS) == 3


def test_no_check_validates_a_mart_against_itself():
    """The tautology, as a structural rule rather than a memory.

    A check whose independent query reads the artefact it is validating is the
    exact defect this module replaced. `mart_command_center_overview` is the
    artefact; no independent side may mention it.
    """
    for check in reconciliation.VALUE_CHECKS:
        assert "mart_command_center_overview" not in check["independent"], \
            check["name"]
        assert "mart_command_center_overview" in check["served"], check["name"]


def test_no_independent_check_reads_a_mart_at_all():
    """Stronger: recompute from BASE models, one layer below the marts.

    Reading a mart would still be independent of the overview table, but it
    would not catch a mart aggregation bug - and that is half the value.
    """
    for check in reconciliation.VALUE_CHECKS:
        assert "mart_" not in check["independent"], check["name"]
