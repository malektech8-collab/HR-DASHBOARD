# -*- coding: utf-8 -*-
"""`iqama_expiry` and `iqama_occupation` are employee attributes.

STEP 2 of the compliance split. THE PERIOD TEST decides where a column
belongs: does the value change with the REPORTING PERIOD?

  gosi_salary        yes - it is re-registered as pay changes   -> GOSI contract
  iqama_expiry       NO  - it changes when the iqama is reissued -> employees
  iqama_occupation   NO  - same                                  -> employees

Both were in a period-grained contract only because that is where the other
compliance columns happened to live. Both are also demonstrably already on a
real KSA HRIS export, so asking for them in a separate compliance file asked
the client to re-supply what they had already sent.

WHY IT IS ONE STEP FOR TWO COLUMNS. Same justification, same seven-model blast
radius, and one shared demo verification.

Per SP-001 each assertion is paired with a tamper.
"""
import io
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402

_MARTS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")

MOVED = ["iqama_expiry", "iqama_occupation"]


def _sql(name):
    with io.open(os.path.join(_MARTS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# the contracts
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column", MOVED)
def test_it_is_on_employees_and_optional(column):
    names = [c["name"] for c in cs.columns("employees")]
    assert column in names
    assert column not in cs.required_columns("employees")


def test_iqama_expiry_has_left_compliance():
    # Checked across all four platform contracts - `compliance` split into
    # one per government platform, so "not on compliance" now means "on none
    # of them".
    for table in ("compliance_gosi", "compliance_qiwa", "compliance_wps",
                  "compliance_health"):
        assert "iqama_expiry" not in [c["name"] for c in cs.columns(table)]


def test_compliance_keeps_what_IS_period_grained():
    """The tamper. Moving the attributes must not empty the contract of the
    facts that genuinely belong to a month."""
    names = [c["name"] for c in cs.columns("compliance_gosi")]
    for column in ("gosi_salary", "gosi_status", "period", "employee_id"):
        assert column in names, column


def test_the_move_is_recorded_where_the_column_used_to_be():
    """A column that vanishes from a contract leaves a reader guessing. The
    tombstone says where it went and why."""
    # The tombstone travelled with the split. It sits on the QIWA contract,
    # where it was adjacent to work_permit_expiry - the other expiry a platform
    # export carries - which is where a reader looking for it will land.
    text = io.open(os.path.join(_ROOT, "data", "contracts",
                                "compliance_qiwa_schema.yml"),
                   encoding="utf-8").read()
    assert "iqama_expiry MOVED to the employees contract" in text
    assert "period test" in text


@pytest.mark.parametrize("column", MOVED)
def test_the_description_states_the_period_test(column):
    spec = next(c for c in cs.columns("employees") if c["name"] == column)
    assert spec["description_en"].strip()
    assert spec["description_ar"].strip()
    assert "OPTIONAL" in spec["description_en"]


# --------------------------------------------------------------------------
# nothing still reads them from the compliance side
# --------------------------------------------------------------------------

def test_no_model_reads_iqama_from_the_compliance_alias():
    """The whole point of the move. A leftover `c.iqama_expiry` would break
    the moment the compliance contract splits."""
    offenders = []
    for name in sorted(os.listdir(_MARTS)):
        if not name.endswith(".sql"):
            continue
        if "c.iqama_expiry" in _sql(name) or "c.iqama_occupation" in _sql(name):
            offenders.append(name)
    assert not offenders, offenders


def test_the_seam_carries_them():
    """base_compliance_current is where eleven models read these. Taking them
    from the employees side there is why none of the eleven changed."""
    sql = _sql("base_compliance_current.sql")
    assert "e.iqama_expiry" in sql
    assert "e.iqama_occupation" in sql


def test_the_expiring_iqama_check_no_longer_requires_a_compliance_row():
    """It was an INNER join to compliance, so an employee with an expiring
    iqama and no compliance row was never flagged - a real finding suppressed
    by where the column happened to live."""
    sql = _sql("mart_workforce_exceptions.sql")
    arm = sql[sql.index("Iqama Expiry Risk"):]
    arm = arm[:arm.index("UNION ALL")]
    assert "stg_compliance" not in arm
    assert "e.iqama_expiry" in arm


# --------------------------------------------------------------------------
# the sample moved the values, not just the column
# --------------------------------------------------------------------------

def test_the_sample_moved_the_values_to_the_same_employees():
    """Demo byte-identity depends on WHICH employees carry a value, not only
    on the column existing. Two employees had one; two still do."""
    source = io.open(os.path.join(_ROOT, "scripts", "generate_sample_data.py"),
                     encoding="utf-8").read()
    employees = source[source.index("    employees = ["):]
    employees = employees[:employees.index("\n    ]")]
    assert '"2026-12-31", "Software Engineer"' in employees
    assert '"2026-11-01", "Accountant"' in employees
    # and none of the four platform samples carries the column
    for name in ("compliance_gosi", "compliance_qiwa", "compliance_wps",
                 "compliance_health"):
        block = source[source.index("    {} = [".format(name)):]
        block = block[:block.index("\n    ]")]
        assert "iqama_expiry" not in block, name


def test_the_sample_header_and_rows_agree():
    """The tamper for the move: a column added to the header and not the rows
    shifts every field after it, silently."""
    import csv
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as root:
        env = dict(os.environ, HRDASH_DATA_ROOT=root, DATA_MODE="demo",
                   PYTHONIOENCODING="utf-8")
        result = subprocess.run(
            [sys.executable, os.path.join(_ROOT, "scripts",
                                          "generate_sample_data.py")],
            cwd=_ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr[-800:]
        path = os.path.join(root, "data", "sample", "employees_sample.csv")
        with io.open(path, encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]
    assert header[-2:] == ["iqama_expiry", "iqama_occupation"]
    assert all(len(row) == len(header) for row in body)
    carrying = [row for row in body if row[header.index("iqama_expiry")]]
    assert len(carrying) == 2, "two employees carried an iqama expiry before"
