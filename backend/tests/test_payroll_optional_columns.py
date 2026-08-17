# -*- coding: utf-8 -*-
"""Five payroll columns relaxed, and the arithmetic that made it dangerous.

WHY THIS CYCLE EXISTED. Payroll was 13 of 13 required with zero optional -
written from the sample rather than from what a real export carries. The
employees load found the same thing the expensive way, one rejected upload at
a time.

WHY IT IS NOT A ONE-LINE CONTRACT CHANGE. `required: false` alone accepts the
file and then produces WRONG NUMBERS - not a crash, which is the employees
lesson in a worse form. Two shapes, both measured in DuckDB:

    SUM(housing + transport + other)  with other all NULL  ->  0.0
        `a + b + NULL` is NULL for the whole row and SUM skips it, so an
        absent other_allowances did not omit itself - it DISCARDED HOUSING
        AND TRANSPORT and reported zero.

    ABS(gross - (basic + ... + NULL)) > 0.01   ->  0 rows
        the component-reconciliation check does not lose precision, it STOPS
        FIRING, and every row passes.

gross_pay and net_pay stay required: a payroll file without them is not
payroll.

Per SP-001 each assertion is paired with a tamper.
"""
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402

_MODELS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")

RELAXED = ["cost_center", "other_allowances", "overtime_amount",
           "deductions", "location"]
STILL_REQUIRED = ["gross_pay", "net_pay", "employee_id", "payroll_period",
                  "basic_salary", "housing_allowance", "transport_allowance",
                  "payroll_status"]


def _sql(name):
    with open(os.path.join(_MODELS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column", RELAXED)
def test_the_five_are_optional(column):
    assert column not in cs.required_columns("payroll")


@pytest.mark.parametrize("column", STILL_REQUIRED)
def test_everything_else_still_stands(column):
    """The tamper. A relaxation that loosened the whole contract would pass
    the test above while making the gate meaningless."""
    assert column in cs.required_columns("payroll")


def test_gross_and_net_are_kept_deliberately():
    """Ruled explicitly: a payroll file without them is not payroll."""
    required = cs.required_columns("payroll")
    assert "gross_pay" in required and "net_pay" in required
    assert len(required) == 8


@pytest.mark.parametrize("column", RELAXED)
def test_each_relaxed_column_says_what_absence_MEANS(column):
    """An optional column whose description does not say what happens when it
    is missing leaves the operator to guess - and the guess is always that the
    figure is zero."""
    spec = next(c for c in cs.columns("payroll") if c["name"] == column)
    english = spec["description_en"]
    assert "OPTIONAL" in english, column
    assert spec["description_ar"].strip()
    assert "اختياري" in spec["description_ar"], column


# --------------------------------------------------------------------------
# the arithmetic - measured, not asserted from memory
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def con():
    connection = duckdb.connect()
    connection.execute(
        "CREATE TABLE p AS SELECT * FROM (VALUES "
        "(100.0, 50.0, NULL), (200.0, 60.0, NULL)) t(housing, transport, other)")
    yield connection
    connection.close()


def test_the_naive_composite_sum_loses_the_columns_beside_it(con):
    """The defect this cycle had to fix BEFORE relaxing. Not a crash - a
    confident zero, with housing and transport inside it."""
    naive = con.execute(
        "SELECT COALESCE(SUM(housing + transport + other), 0.0) FROM p"
    ).fetchone()[0]
    assert naive == 0.0, "if this stops being 0.0 the guard below is unneeded"


def test_the_shipped_composite_keeps_what_was_supplied(con):
    """COALESCE inside the row expression, so the components the client DID
    send still count."""
    fixed = con.execute(
        "SELECT COALESCE(SUM(housing + transport + COALESCE(other, 0.0)), 0.0) "
        "FROM p").fetchone()[0]
    assert fixed == 410.0


def test_a_null_component_silently_disables_the_reconciliation_check(con):
    """The more serious half: the check does not lose precision, it stops
    firing. NULL > 0.01 is not true, so every row passes."""
    con.execute("CREATE TABLE q AS SELECT * FROM (VALUES "
                "(999.0, 100.0, NULL)) t(gross, basic, other)")
    flagged = con.execute(
        "SELECT COUNT(*) FROM q WHERE ABS(gross - (basic + other)) > 0.01"
    ).fetchone()[0]
    assert flagged == 0, "the premise of the gate below"
    # And with the component present, the same row IS caught - the tamper.
    caught = con.execute(
        "SELECT COUNT(*) FROM q WHERE ABS(gross - (basic + COALESCE(other, 0.0))) "
        "> 0.01").fetchone()[0]
    assert caught == 1


# --------------------------------------------------------------------------
# the models carry the gates
# --------------------------------------------------------------------------

def test_no_naive_composite_survives_in_any_mart():
    """The rule, not a list of the ones we remembered."""
    offenders = []
    for name in sorted(os.listdir(_MODELS)):
        if not name.endswith(".sql"):
            continue
        sql = _sql(name)
        if "transport_allowance + other_allowances" in sql:
            for line in sql.splitlines():
                stripped = line.strip()
                if ("transport_allowance + other_allowances" in stripped
                        and not stripped.startswith("--")
                        and "COALESCE(other_allowances" not in stripped):
                    # permitted only inside a gated expression
                    if "has_payroll" not in sql:
                        offenders.append("{}: {}".format(name, stripped[:60]))
    assert not offenders, offenders


@pytest.mark.parametrize("model,var", [
    ("mart_payroll_kpis.sql", "has_payroll_overtime_sql"),
    ("mart_payroll_kpis.sql", "has_payroll_deductions_sql"),
    ("mart_payroll_components.sql", "has_payroll_other_allowances_sql"),
    ("mart_payroll_exceptions.sql", "has_payroll_other_allowances_sql"),
    ("mart_exec_kpis.sql", "has_payroll_overtime_sql"),
])
def test_the_gate_reaches_the_model(model, var):
    assert var in _sql(model)


def test_the_component_check_is_gated_on_both_components():
    """Gross cannot be reconciled against components the client did not send,
    so the check is withheld rather than passing every row."""
    sql = _sql("mart_payroll_exceptions.sql")
    assert "has_payroll_other_allowances_sql" in sql
    assert "has_payroll_overtime_sql" in sql


def test_the_vars_are_resolved_per_client_not_defaulted():
    """A var defaulted in dbt_project.yml but never overridden is a decision
    this repository made for every client."""
    with open(os.path.join(_ROOT, "scripts", "build_warehouse.py"),
              encoding="utf-8") as handle:
        source = handle.read()
    for var in ("has_payroll_other_allowances_sql", "has_payroll_overtime_sql",
                "has_payroll_deductions_sql"):
        assert var in source, var
    assert 'provides_column("payroll", "overtime_amount")' in source
