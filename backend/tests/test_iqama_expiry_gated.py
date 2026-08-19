# -*- coding: utf-8 -*-
"""An absent iqama column means UNKNOWN, never "0 expired".

THE P0. An expired iqama means an employee cannot legally work and the penalty
lands on the employer. Every iqama figure in the product is a COUNT over
`employees.iqama_expiry`, and the first real client's export does not carry
that column - so, measured on their build before this cycle:

    iqamas_expired                    -> 0       'nobody's iqama has expired'
    iqamas_expiring_30                -> 0       'nothing expires this month'
    mart_workforce_iqama_expiry       -> 0,0,0,0,0,2047
    'Missing Iqama Expiry Date' rows  -> 2047 of 2047 non-Saudi employees

Six buckets making three false claims from one absent column, and one exception
per employee about their EXPORT FORMAT - the manager_id shape, at full scale.

WHY IT WAS NOT FOUND EARLIER, which is SP-013 and the reason this file exists:
the registry wrongly suppressed these marts on a compliance file they never
read, so the zeros never reached a screen. TWO DEFECTS CANCELLED. Correcting
the suppression - which was right - is what exposed the fabrication underneath.

AND A THIRD UNDER BOTH. The gate could not have been wired even had someone
thought to: a tolerate-absence branch in ingest_raw materialised the column as
a typed NULL BEFORE complete_canonical_shape() was asked which columns were
absent, so the absence was ERASED BEFORE IT WAS RECORDED and
provides_column("employees", "iqama_expiry") answered TRUE for a client with no
such column. Both halves were needed; the first two sections below are the two
halves.

Per SP-001 each assertion is paired with a tamper.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs      # noqa: E402
import onboarding as onb           # noqa: E402

_MARTS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")
_VAR = "has_iqama_expiry_source_sql"


def _sql(name):
    with io.open(os.path.join(_MARTS, name), encoding="utf-8") as handle:
        return handle.read()


def _strip_comments(sql):
    return "\n".join(line.split("--")[0] for line in sql.splitlines())


def _strip_python_comments(source):
    """PROSE HAS NOW TRIPPED A STRUCTURAL RULE IN THIS REPOSITORY FOUR TIMES,
    and the fourth was this file: the comment explaining the fix QUOTES THE OLD
    CODE, so a rule that scans for the old code found it in its own epitaph.

    A rule about Python must read Python, exactly as the rule about SQL must
    read SQL. Naive but sufficient here - the lines it scans contain no `#`
    inside a string literal, and the assertion below would fail loudly rather
    than quietly if that changed."""
    return "\n".join(line.split("#")[0] for line in source.splitlines())


# --------------------------------------------------------------------------
# half one - the absence must SURVIVE ingest to be recordable
# --------------------------------------------------------------------------

def test_the_absence_is_recorded_when_the_column_is_missing():
    """The root cause. Nothing downstream can gate on a fact that was erased
    three lines before it was recorded."""
    frame = pl.DataFrame({"employee_id": ["E1"], "employee_name": ["A"]})
    completed, absent = onb.complete_canonical_shape(frame, "employees")
    assert "iqama_expiry" in absent
    assert "iqama_expiry" in completed.columns   # and it still binds downstream


def test_ingest_does_not_fill_the_column_before_recording_it():
    """The tamper for the fix, read off the source: the else-arm that
    materialised `iqama_expiry` must not come back. It is not enough that the
    column ends up typed-NULL - WHO fills it decides whether the absence is
    knowable, and only complete_canonical_shape() reports what it filled."""
    source = io.open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                     encoding="utf-8").read()
    body = _strip_python_comments(source)
    assert 'pl.lit(None, dtype=pl.Date).alias("iqama_expiry")' not in body
    # the cast still happens, but only for a file that supplies the column
    assert 'if "iqama_expiry" in df.columns:' in body


def test_provides_column_answers_false_for_a_file_without_it():
    """End to end on the recorded fact, in an isolated data root so the real
    registry is untouched."""
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "provided_columns.yml")
        onb.record_provided_columns("employees", ["iqama_expiry"], path=path)
        assert onb.provides_column("employees", "iqama_expiry", path=path) is False
        # the tamper: a column NOT recorded absent must stay provided, or the
        # gate would darken every figure rather than the right one
        assert onb.provides_column("employees", "joining_date", path=path) is True


# --------------------------------------------------------------------------
# half two - every figure derived from it is gated
# --------------------------------------------------------------------------

_COUNT_SITES = [
    ("mart_workforce_iqama_expiry.sql", 6),   # all six buckets
    ("mart_compliance_kpis.sql", 2),          # iqamas_expired / _expiring_30
    ("mart_workforce_kpis.sql", 1),           # iqama_expiring_30
    ("mart_document_expiry.sql", 1),          # iqama_count over the spine
]


@pytest.mark.parametrize("name,expected", _COUNT_SITES)
def test_every_iqama_count_is_gated(name, expected):
    sql = _strip_comments(_sql(name))
    assert sql.count(_VAR) == expected, name


def test_the_missing_date_bucket_is_gated_too():
    """The bucket that read 2,047. Gating only the expiry buckets would leave
    'every one of your employees is missing a date' - true of the file, and
    presented as a finding about the employees."""
    sql = _strip_comments(_sql("mart_workforce_iqama_expiry.sql"))
    arm = sql[sql.index("missing_date") - 400:]
    assert _VAR in arm[:arm.index("missing_date")]


@pytest.mark.parametrize("name", [
    "mart_workforce_exceptions.sql",
])
def test_the_per_employee_arms_are_gated(name):
    """Both iqama arms - the expiry-risk one and the missing-date one."""
    sql = _strip_comments(_sql(name))
    assert sql.count(_VAR) == 2, name


def test_the_seam_makes_the_bucket_unmeasurable_rather_than_missing_date():
    """`missing_date` and NULL are DIFFERENT FINDINGS. A client who records
    iqama expiry and left one blank has a data-quality exception; a client with
    no iqama column has a coverage fact, and calling the second the first is
    the whole defect."""
    sql = _strip_comments(_sql("base_document_expiry.sql"))
    bucket = sql[sql.index("AS iqama_bucket") - 900:sql.index("AS iqama_bucket")]
    assert "NOT {{ var('%s') }} THEN NULL" % _VAR in bucket
    # and it comes FIRST, or `IS NULL THEN 'missing_date'` wins
    assert bucket.index(_VAR) < bucket.index("'missing_date'")


def test_the_three_compliance_arms_ride_the_seam():
    """They compare against the bucket, so a NULL bucket withholds them with no
    edit. Pinned, because it is the reason those three arms have no var and a
    reader would otherwise read that as an omission."""
    sql = _strip_comments(_sql("mart_compliance_exceptions.sql"))
    for literal in ("iqama_bucket = 'missing_date'",
                    "iqama_bucket = 'expired'",
                    "iqama_bucket = '0_30'"):
        assert literal in sql, literal


# --------------------------------------------------------------------------
# the gate is wired to the registry, not to a config literal
# --------------------------------------------------------------------------

def test_the_var_resolves_from_provenance():
    source = io.open(os.path.join(_ROOT, "scripts", "build_warehouse.py"),
                     encoding="utf-8").read()
    block = source[source.index('"%s"' % _VAR):]
    block = block[:block.index("else")]
    assert '_onb.provides_column("employees", "iqama_expiry")' in block


def test_the_var_has_a_compile_time_default():
    """dbt must compile without build_warehouse - and TRUE keeps demo, which
    supplies the column, unchanged."""
    text = io.open(os.path.join(_ROOT, "dbt_analytics", "dbt_project.yml"),
                   encoding="utf-8").read()
    assert re.search(r"^\s+%s:\s*\"TRUE\"" % _VAR, text, re.M)


def test_no_iqama_figure_is_left_ungated():
    """The completeness tamper, and the one that catches the NEXT iqama figure
    somebody adds: any model that both reads the column (or its bucket) and
    aggregates or filters on it must name the gate."""
    offenders = []
    for name in sorted(os.listdir(_MARTS)):
        if not name.endswith(".sql"):
            continue
        sql = _strip_comments(_sql(name))
        reads = "iqama_expiry" in sql or "iqama_bucket" in sql
        if not reads:
            continue
        gated = _VAR in sql
        # base_document_expiry IS the seam; the compliance arms ride it
        rides_the_seam = name == "mart_compliance_exceptions.sql"
        # these two only carry the column through to a row-level display,
        # where NULL renders as a blank and claims nothing
        passthrough = name in ("base_compliance_current.sql",
                               "base_government_platform_records.sql")
        if not (gated or rides_the_seam or passthrough):
            offenders.append(name)
    assert not offenders, offenders


# --------------------------------------------------------------------------
# demo is unchanged - the tamper for the whole cycle
# --------------------------------------------------------------------------

def test_demo_supplies_the_column_so_nothing_is_withheld_there():
    """If the gate darkened demo, it would be darkening clients who DO supply
    iqama expiry - the opposite error, and SP-011's species."""
    assert "iqama_expiry" in [c["name"] for c in cs.columns("employees")]
    with tempfile.TemporaryDirectory() as root:
        env = dict(os.environ, HRDASH_DATA_ROOT=root, DATA_MODE="demo",
                   PYTHONIOENCODING="utf-8")
        result = subprocess.run(
            [sys.executable, os.path.join(_ROOT, "scripts",
                                          "generate_sample_data.py")],
            cwd=_ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr[-800:]
        path = os.path.join(root, "data", "sample", "employees_sample.csv")
        header = io.open(path, encoding="utf-8").readline()
    assert "iqama_expiry" in header
