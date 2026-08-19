# -*- coding: utf-8 -*-
"""Lateness is UNMEASURED without a schedule, not zero.

THE DEFECT THIS REMOVES was created by the previous cycle and carried here
deliberately, to be tested against a real shape rather than reasoned about.

`scheduled_start` became optional when the attendance inversion was corrected -
a biometric terminal produces punches, a roster needs a rostering system. The
lateness calculation kept an `ELSE 0`, so every client without a roster got:

    late_minutes              -> 0        "nobody was ever late"
    attendance_compliance_pct -> computed from two of its three terms,
                                 rising toward 100%

The second is the serious one. mart_attendance_kpis' own comment says the
figure must not "look best exactly when the data is thinnest" - and it arrived
there anyway, by another route.

Measured, before and after:

    late minutes, OLD COALESCE(...,0) -> 0      'nobody was ever late'
    late minutes, NEW (no coalesce)   -> None   not measured
    compliance_pct computed anyway    -> 0.333  served as "attendance compliance"

Per SP-001 each assertion is paired with a tamper.
"""
import datetime
import os
import sys

import duckdb
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs   # noqa: E402
import derivations as der       # noqa: E402
import ingest_raw               # noqa: E402

_MARTS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")


def _sql(name):
    with open(os.path.join(_MARTS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column", [
    "excused_late_minutes",   # an adjudication
    "overtime_approved",      # an approval-workflow flag
    "late_minutes",           # derivable when its inputs exist
])
def test_relaxed(column):
    assert column not in cs.required_columns("attendance")


@pytest.mark.parametrize("column", [
    "attendance_date", "employee_id", "actual_check_in", "actual_check_out",
])
def test_the_things_a_biometric_terminal_actually_produces_stay_required(column):
    """The tamper. Relaxing the computed columns must not loosen the observed
    ones - those are the reason the inversion was corrected."""
    assert column in cs.required_columns("attendance")


def test_late_minutes_declares_the_inputs_it_actually_needs():
    spec = next(c for c in cs.columns("attendance") if c["name"] == "late_minutes")
    assert der.source_columns(spec) == ["actual_check_in", "scheduled_start"]
    assert spec["derivation"] == "late_minutes"


# --------------------------------------------------------------------------
# SP-006's boundary condition
# --------------------------------------------------------------------------

def test_derived_when_the_schedule_exists():
    assert der.late_minutes(
        ["2026-06-01 08:20:00", "2026-06-01 08:00:00"],
        ["2026-06-01 08:00:00", "2026-06-01 08:00:00"], 15) == [5, 0]


def test_WITHHELD_when_the_schedule_does_not():
    """The boundary condition, and the whole point: "derive it always" assumes
    the inputs are always there. Here one of them is itself optional, so
    deriving unconditionally would put the zeroing one layer along."""
    assert der.late_minutes(["2026-06-01 09:00:00"], [None], 15) == [None]


def test_a_missing_PUNCH_is_zero_not_null():
    """A punch that never happened is a missing punch - counted by
    missing_punch_count - not an unmeasurable lateness. The two absences mean
    different things and must not collapse."""
    assert der.late_minutes([None], ["2026-06-01 08:00:00"], 15) == [0]


def test_the_grace_period_comes_from_the_config_dbt_reads():
    """If ingest derived lateness with a different grace period than dbt, the
    two would disagree about the same quantity - and the disagreement would
    look like the CLIENT's system being wrong."""
    assert ingest_raw._grace_period_minutes() == 15
    assert der.needs_parameter("late_minutes")


def test_the_grace_period_actually_changes_the_answer():
    """The tamper for the wiring above: a parameter nothing reads would pass
    the test before it."""
    args = (["2026-06-01 08:20:00"], ["2026-06-01 08:00:00"])
    assert der.late_minutes(*args, 15) == [5]
    assert der.late_minutes(*args, 0) == [20]


# --------------------------------------------------------------------------
# the marts withhold rather than zero
# --------------------------------------------------------------------------

def test_the_base_model_no_longer_zeroes_lateness():
    sql = _sql("base_attendance_current.sql")
    assert "WHEN a.scheduled_start IS NULL THEN NULL" in sql


def _select_item(figure):
    """The SQL of ONE select item, ending at its alias.

    A fixed-size window picks up the neighbouring item's gate - which is how
    the first version of this test failed while the code was correct. This
    walks back to the start of the item instead.
    """
    sql = _sql("mart_attendance_kpis.sql")
    end = sql.index("AS {}".format(figure))
    head = sql[:end]
    depth, start = 0, 0
    for position in range(len(head) - 1, -1, -1):
        char = head[position]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
        elif char == "," and depth == 0:
            start = position + 1
            break
    return head[start:]


@pytest.mark.parametrize("figure", [
    "attendance_compliance_pct", "late_minutes", "net_late_minutes",
    "early_leave_minutes",
])
def test_every_schedule_dependent_figure_is_gated(figure):
    assert "has_attendance_schedule_source_sql" in _select_item(figure), figure


def test_excused_late_minutes_is_NOT_gated_on_the_schedule():
    """The tamper. It is relaxed for a different reason - it is an
    adjudication, not a schedule-dependent measurement - and gating it here
    would withhold a figure the client CAN supply without a roster."""
    assert "has_attendance_schedule_source_sql" not in \
        _select_item("excused_late_minutes")


def test_the_measured_difference_the_gate_exists_for():
    con = duckdb.connect()
    con.execute("CREATE TABLE a AS SELECT * FROM (VALUES "
                "(NULL, 0, 0.0), (NULL, 1, 0.0), (NULL, 0, 1.0)) "
                "t(net_late, punches, absence)")
    assert con.execute(
        "SELECT COALESCE(SUM(net_late), 0) FROM a").fetchone()[0] == 0
    assert con.execute("SELECT SUM(net_late) FROM a").fetchone()[0] is None
    # and the percentage would still have computed, from two of three terms
    pct = con.execute(
        "SELECT 1.0 - (COUNT(CASE WHEN net_late>0 OR punches>0 OR absence>0 "
        "THEN 1 END)/CAST(COUNT(absence) AS DOUBLE)) FROM a").fetchone()[0]
    assert pct is not None and 0 < pct < 1
    con.close()


# --------------------------------------------------------------------------
# ingest
# --------------------------------------------------------------------------

def test_every_derived_attendance_column_has_an_ingest_branch():
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    for column in ("late_minutes", "net_late_minutes", "missing_punch_count"):
        assert '_derive_if_absent(df, "attendance", "{}"'.format(column) in source


def test_late_minutes_is_derived_BEFORE_net_late_minutes_reads_it():
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    assert source.index('"attendance", "late_minutes"') < \
        source.index('"attendance", "net_late_minutes"')


# --------------------------------------------------------------------------
# shape completion and provision recording - both halves, every contracted table
# --------------------------------------------------------------------------

def _is_wired(table, source):
    """Is this table shape-completed and recorded at ingest?

    Either by a literal call, or by being named in a MODULE CONSTANT the loop
    iterates. A loop is invisible to a rule that greps for the literal, and the
    four government-platform tables are ingested in one - so the constant is
    what makes the loop legible to this check rather than the check being
    weakened to accept anything.
    """
    if ('_complete_and_record(df, "{}")'.format(table) in source
            or 'complete_canonical_shape(df, "{}")'.format(table) in source
            or 'record_provided_columns("{}"'.format(table) in source):
        return True
    return any(name == table for name, _casts in ingest_raw.COMPLIANCE_PLATFORMS)


CONTRACTED_WITH_OPTIONALS = [
    "employees", "payroll", "attendance", "compliance_gosi",
    "compliance_qiwa", "compliance_wps", "compliance_health",
    "employee_relations", "hr_requests",
]


@pytest.mark.parametrize("table", CONTRACTED_WITH_OPTIONALS)
def test_every_relaxed_table_is_shape_completed(table):
    """`required: false` alone accepts the file and then crashes downstream.
    complete_canonical_shape was wired for employees ONLY, so every relaxation
    after it was a latent ColumnNotFoundError. Measured on a schedule-less
    attendance file before this was fixed:

        scheduled_start cast RAISES: ColumnNotFoundError
    """
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    assert _is_wired(table, source),         "{} has optional columns and is never shape-completed".format(table)


@pytest.mark.parametrize("table", CONTRACTED_WITH_OPTIONALS)
def test_every_relaxed_table_records_what_was_absent(table):
    """THE SILENT HALF. provides_column() defaults to TRUE, so a domain that
    never records its absences makes every has_*_source_sql gate resolve TRUE -
    and the withheld figures those gates protect get served anyway. The gate is
    present, correct and unreachable."""
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    assert _is_wired(table, source),         "{} never records absences; its gates cannot fire".format(table)


def test_completion_and_recording_land_together():
    """The tamper. Recording without completing leaves the crash; completing
    without recording leaves the gates dark. One helper does both so they
    cannot drift apart."""
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    body = source[source.index("def _complete_and_record("):]
    body = body[:body.index("\ndef ")]
    assert "complete_canonical_shape" in body
    assert "record_provided_columns" in body


def test_a_schedule_less_attendance_file_survives_ingest(tmp_path, monkeypatch):
    """End to end: the file a biometric terminal produces. It must complete,
    record, and leave the schedule gate resolving FALSE."""
    import polars as pl
    import onboarding as onb
    monkeypatch.setenv("HRDASH_DATA_ROOT", str(tmp_path))
    frame = pl.DataFrame({
        "attendance_date": ["2026-06-01"], "employee_id": ["E1"],
        "actual_check_in": ["2026-06-01 08:20:00"],
        "actual_check_out": ["2026-06-01 17:00:00"],
        "absence_days": ["0"], "overtime_hours": ["0"], "location": ["RUH"],
    })
    completed = ingest_raw._complete_and_record(frame, "attendance")
    assert "scheduled_start" in completed.columns      # no ColumnNotFoundError
    assert onb.provides_column("attendance", "scheduled_start") is False
    # and the tamper: a column the file DID supply is still reported provided
    assert onb.provides_column("attendance", "actual_check_in") is True


# --------------------------------------------------------------------------
# SP-009 - the expiry condition of a "safe" default, as a test
# --------------------------------------------------------------------------

def test_any_table_with_a_relaxed_column_records_its_absences():
    """SP-009's expiry condition, written as a test rather than a comment.

    `provides_column()` defaults to True. That was correct while only employees
    recorded absences, and became wrong the moment a second domain relaxed a
    column - with nothing announcing the transition. Every has_*_source_sql
    gate reading an unrecorded table resolves TRUE, so the gate is present,
    correct, and unreachable.

    This is the day-it-stops-holding alarm: a table that has optional columns
    must be wired for recording, or the gates that read them are dark.
    """
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    dark = []
    for table in cs.available_tables():
        optional = [c["name"] for c in cs.columns(table)
                    if c["name"] not in cs.required_columns(table)]
        if not optional:
            continue
        wired = _is_wired(table, source)
        if not wired:
            dark.append("{} ({} optional column(s))".format(table, len(optional)))
    assert not dark, (
        "these tables have relaxed columns but never record absences, so "
        "provides_column() answers True and every gate reading them is "
        "dark:\n  " + "\n  ".join(dark))
