# -*- coding: utf-8 -*-
"""The GOSI-versus-payroll comparison spans two domains, and needs both.

STEP 3 of the compliance split. `payroll_basic_salary` was a column on the
COMPLIANCE contract holding a figure the client had already sent us in their
payroll file. It existed so `gosi_salary` could be compared against what
payroll actually paid - a real and valuable regulatory finding, since a GOSI
salary below actual pay understates contributions and surfaces in an audit.

But it asked the client to copy payroll figures into a compliance export so
that we could compare two numbers we already hold, and REJECTED THEIR FILE when
they could not. Same species as the derived columns.

THE COMPARISON NOW SPANS DOMAINS, so it must survive each side being absent:

    GOSI export, no payroll   -> nothing to compare against   -> WITHHELD
    payroll, no GOSI export   -> nothing to compare with      -> WITHHELD
    both                      -> the real finding
    neither                   -> withheld, and the page is suppressed anyway

Withheld rather than silent. With one side absent the old `IS NOT NULL` guards
already made the mismatch arm produce nothing - which reads as "GOSI and
payroll agree", a fabricated-favourable answer about a regulatory figure.

Per SP-001 each assertion is paired with a tamper.
"""
import io
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402

_MARTS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")


def _sql(name):
    with io.open(os.path.join(_MARTS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# the column is gone, and its absence is explained
# --------------------------------------------------------------------------

def test_payroll_basic_salary_has_left_the_compliance_contract():
    assert "payroll_basic_salary" not in [c["name"] for c in cs.columns("compliance")]


def test_the_removal_is_recorded_where_the_column_used_to_be():
    text = io.open(os.path.join(_ROOT, "data", "contracts",
                                "compliance_schema.yml"), encoding="utf-8").read()
    assert "payroll_basic_salary REMOVED" in text
    assert "already hold" in text


def test_gosi_salary_stays_because_only_GOSI_can_supply_it():
    """The tamper. Removing the copied column must not remove the fact it was
    compared against - gosi_salary comes from the GOSI platform and nothing
    else in the pipeline can produce it."""
    assert "gosi_salary" in cs.required_columns("compliance")


def test_the_pay_column_set_no_longer_names_it():
    source = io.open(os.path.join(_ROOT, "scripts", "validate_schema.py"),
                     encoding="utf-8").read()
    assert '"payroll_basic_salary"' not in source
    assert '"gosi_salary"' in source


# --------------------------------------------------------------------------
# it now comes from the payroll domain
# --------------------------------------------------------------------------

def test_the_seam_takes_it_from_payroll():
    sql = _sql("base_compliance_current.sql")
    assert "pay.basic_salary AS payroll_basic_salary" in sql
    assert "base_payroll_current" in sql
    # the NAME is kept, so downstream reads unchanged
    assert "c.payroll_basic_salary" not in sql


def test_the_payroll_join_cannot_multiply_compliance_rows():
    """base_payroll_current is one row per payroll LINE. A duplicate line would
    otherwise multiply every compliance row for that employee, changing counts
    on a page that has nothing to do with payroll."""
    for model in ("base_compliance_current.sql",
                  "base_government_platform_records.sql"):
        sql = _sql(model)
        block = sql[sql.index("base_payroll_current"):]
        assert "GROUP BY employee_id" in block, model


def test_the_compliance_first_model_joins_payroll_DIRECTLY():
    """base_government_platform_records is compliance-first on purpose, so a
    compliance row for an unknown employee keeps its 'Unknown Employee'
    classification. Reading through the employees-first view would silently
    drop exactly the rows it exists to surface."""
    sql = _sql("base_government_platform_records.sql")
    assert "FROM {{ ref('stg_compliance') }} c" in sql
    # not the ref - the NAME appears in the comment explaining why it is not
    # used, which is exactly the text a cruder assertion would trip over.
    assert "ref('base_compliance_current')" not in sql
    assert "Unknown Employee" in sql


# --------------------------------------------------------------------------
# both sides required - the asymmetric cases
# --------------------------------------------------------------------------

@pytest.mark.parametrize("arm", ["GOSI Salary Mismatch", "Missing Salary Info"])
def test_each_arm_needs_BOTH_domains(arm):
    sql = _sql("mart_compliance_exceptions.sql")
    block = sql[sql.index(arm):]
    block = block[:block.index("UNION ALL")]
    assert "has_gosi_source_sql" in block, arm
    assert "has_payroll_domain_sql" in block, arm


def test_the_missing_salary_arm_was_the_dangerous_one():
    """It fires when EITHER value is null, so a client with no GOSI export -
    every gosi_salary null - got one CRITICAL row per employee about a file
    they never sent. The manager_id shape, on the highest-stakes page."""
    con = duckdb.connect()
    con.execute("CREATE TABLE c AS SELECT * FROM (VALUES "
                "(NULL, 12000.0), (NULL, 15000.0), (NULL, 11000.0)) "
                "t(gosi_salary, payroll_basic_salary)")
    ungated = con.execute(
        "SELECT COUNT(*) FROM c WHERE gosi_salary IS NULL "
        "OR payroll_basic_salary IS NULL").fetchone()[0]
    assert ungated == 3, "one Critical row per employee, about an absent file"
    # gated: the same rows produce nothing
    gated = con.execute(
        "SELECT COUNT(*) FROM c WHERE FALSE AND (gosi_salary IS NULL "
        "OR payroll_basic_salary IS NULL)").fetchone()[0]
    assert gated == 0
    con.close()


def test_the_mismatch_arm_went_SILENT_rather_than_noisy():
    """The other asymmetry, and why withholding matters. With one side absent
    the IS NOT NULL guards already produced nothing - which reads as 'GOSI and
    payroll agree' about a figure that was never compared."""
    con = duckdb.connect()
    con.execute("CREATE TABLE c AS SELECT * FROM (VALUES "
                "(NULL, 12000.0), (NULL, 15000.0)) t(gosi_salary, pay)")
    quiet = con.execute(
        "SELECT COUNT(*) FROM c WHERE gosi_salary IS NOT NULL "
        "AND pay IS NOT NULL AND gosi_salary != pay").fetchone()[0]
    assert quiet == 0, "silence that reads as agreement"
    # and with both sides present it finds the real disagreement - the tamper
    con.execute("CREATE TABLE d AS SELECT * FROM (VALUES "
                "(9000.0, 12000.0), (15000.0, 15000.0)) t(gosi_salary, pay)")
    found = con.execute(
        "SELECT COUNT(*) FROM d WHERE gosi_salary IS NOT NULL "
        "AND pay IS NOT NULL AND gosi_salary != pay").fetchone()[0]
    assert found == 1
    con.close()


def test_the_payroll_domain_gate_resolves_from_provenance():
    """SP-009's rule, which the general gate test also enforces."""
    source = io.open(os.path.join(_ROOT, "scripts", "build_warehouse.py"),
                     encoding="utf-8").read()
    start = source.index('"has_payroll_domain_sql"')
    block = source[start:start + 400]
    assert "load_declared" in block
