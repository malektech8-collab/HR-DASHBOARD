# -*- coding: utf-8 -*-
"""Columns a client was asked to compute for us, corrected to derivations.

THE FINDING. Four contracts required columns that are OUTPUTS of this pipeline
rather than inputs a source system produces - net_late_minutes,
missing_punch_count, sla_breached, occupation_match_status. Requiring them
asked the client to compute our metrics before uploading, and rejected their
file when they could not. `derived_from` / `derivation` already existed and
none of the four used it.

This is a correction of what the column IS. Fewer required columns is the
consequence, not the goal.

THREE ABSENT-COLUMN BEHAVIOURS, each measured and each handled separately:

  SILENT   `sla_breached` - validate_data filtered `== True`, and NULL == True
           is NULL, so an absent column dropped every row and the file
           reported NO SLA BREACHES. A clean bill of health for the domain
           whose entire purpose is SLA tracking. Fixed FIRST: a check that
           goes quiet is worse than one that gets noisy, because noise gets
           noticed.

  MAXIMAL  the net_late mismatch check flagged every row with any lateness
           (COALESCE(col, 0) reads an absent column as the source claiming
           zero); the qiwa and health-insurance arms flagged EVERY row, having
           an explicit IS NULL arm. The manager_id shape.

  SAFE     the OR-chain compliance ratio - measured identical with the column
           NULL and with it 0, because COUNT(CASE..) skips NULL and FALSE
           alike. Recorded because the payroll cycle established the opposite
           reflex, and SP-005 is about premises that carry when they should
           not.

Per SP-001 each assertion is paired with a tamper.
"""
import datetime
import os
import sys

import duckdb
import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs      # noqa: E402
import derivations as der          # noqa: E402
import onboarding as onb           # noqa: E402

_MARTS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")

DERIVED = [
    ("attendance", "net_late_minutes", ["late_minutes", "excused_late_minutes"]),
    ("attendance", "missing_punch_count", ["actual_check_in", "actual_check_out"]),
    ("hr_requests", "sla_breached", ["created_at", "sla_hours", "closed_at"]),
]


def _sql(name):
    with open(os.path.join(_MARTS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# the mechanism - extended without disturbing what used it
# --------------------------------------------------------------------------

def test_is_saudi_is_untouched():
    """The only derived column before this cycle, and single-source. The
    extension is additive or it is a regression."""
    spec = next(c for c in cs.columns("employees") if c["name"] == "is_saudi")
    assert der.source_columns(spec) == ["nationality"]
    assert der.derive_column(spec, ["Saudi", "British"]) == [True, False]


@pytest.mark.parametrize("table,column,sources", DERIVED)
def test_each_column_declares_its_sources(table, column, sources):
    spec = next(c for c in cs.columns(table) if c["name"] == column)
    assert der.source_columns(spec) == sources
    assert spec["derivation"] in der.REGISTRY


@pytest.mark.parametrize("table,column,sources", DERIVED)
def test_each_is_no_longer_required(table, column, sources):
    assert column not in cs.required_columns(table)


def test_contracts_still_carry_no_expressions():
    """The rule that has not changed: a contract NAMES a rule, resolved from a
    registry. Nothing here is compiled or evaluated."""
    for table, column, _ in DERIVED:
        spec = next(c for c in cs.columns(table) if c["name"] == column)
        rule = spec["derivation"]
        assert isinstance(rule, str) and rule.isidentifier()


def test_a_multi_source_rule_needs_every_source():
    """The tamper for the dict form: a caller that forgets a source must fail
    loudly rather than derive from whatever it did pass."""
    spec = next(c for c in cs.columns("attendance")
                if c["name"] == "net_late_minutes")
    with pytest.raises(der.DerivationError) as exc:
        der.derive_column(spec, {"late_minutes": [10]})
    assert "excused_late_minutes" in str(exc.value)


# --------------------------------------------------------------------------
# the rules themselves
# --------------------------------------------------------------------------

def test_net_late_subtracts_and_floors():
    assert der.net_late_minutes(["30", "10", None], ["5", "20", "0"]) \
        == [25, 0, None]


def test_missing_punches_counts_both_ends():
    assert der.missing_punch_count(["08:00", None, None],
                                   ["17:00", "17:00", None]) == [0, 1, 2]


def test_sla_uses_the_run_time_only_for_OPEN_requests():
    """A closed request is judged against when it closed; an open one against
    now, because an open request past its deadline has breached whether or not
    anyone has closed it."""
    now = datetime.datetime(2026, 6, 30)
    out = der.sla_breached(
        ["2026-06-01T00:00:00"] * 3, [24, 24, None],
        ["2026-06-01T12:00:00", "", None], now)
    assert out == [False, True, None]


def test_an_unknowable_sla_is_NULL_never_False():
    """NULL, not False - an unknown SLA is not a met SLA."""
    now = datetime.datetime(2026, 6, 30)
    assert der.sla_breached([None], [24], [None], now) == [None]
    assert der.sla_breached(["2026-06-01T00:00:00"], [None], [None], now) == [None]


def test_the_parameter_is_declared_in_code_not_in_the_contract():
    assert der.needs_parameter("sla_breached")
    assert not der.needs_parameter("net_late_minutes")
    assert not der.needs_parameter("nationality_is_saudi")


# --------------------------------------------------------------------------
# ordering - the is_saudi trap (ruling 4)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("table,column,sources", DERIVED)
def test_a_derived_column_is_never_shape_completed(table, column, sources):
    """complete_canonical_shape EXCLUDES anything carrying `derivation:`,
    because pre-filling it as typed NULL makes ingest's derive-when-absent
    branch skip itself."""
    frame = pl.DataFrame({c["name"]: ["x"] for c in cs.columns(table)
                          if c["name"] != column})
    completed, added = onb.complete_canonical_shape(frame, table)
    assert column not in added
    assert column not in completed.columns


def test_every_derived_column_has_an_ingest_branch():
    """THE TRAP. A contract key landing before the ingest branch leaves the
    column neither completed nor derived, and the first consumer raises
    ColumnNotFoundError. The relax cycle's lesson with the steps reversed."""
    source = open(os.path.join(_ROOT, "scripts", "ingest_raw.py"),
                  encoding="utf-8").read()
    for table, column, _ in DERIVED:
        assert '_derive_if_absent(df, "{}", "{}"'.format(table, column) in source, \
            "{}.{} is declared derived with no ingest branch".format(table, column)


# --------------------------------------------------------------------------
# the three absent-column behaviours
# --------------------------------------------------------------------------

def test_SILENT_the_sla_filter_no_longer_reports_a_clean_file():
    """`NULL == True` is NULL. eq_missing keeps a sparse PROVIDED column
    yielding its real breaches."""
    absent = pl.DataFrame({"sla_breached": [None, None, None]},
                          schema={"sla_breached": pl.Boolean})
    assert absent.filter(pl.col("sla_breached") == True).height == 0  # noqa: E712
    sparse = pl.DataFrame({"sla_breached": [True, None, False]},
                          schema={"sla_breached": pl.Boolean})
    assert sparse.filter(pl.col("sla_breached").eq_missing(True)).height == 1


def test_SILENT_validate_data_gates_and_says_so():
    source = open(os.path.join(_ROOT, "scripts", "validate_data.py"),
                  encoding="utf-8").read()
    assert "eq_missing(True)" in source
    assert 'provides_column("hr_requests", "sla_breached")' in source
    assert "rather than reported clean" in source


@pytest.mark.parametrize("model,var", [
    ("mart_attendance_exceptions.sql", "has_attendance_net_late_source_sql"),
    ("mart_compliance_exceptions.sql", "has_qiwa_source_sql"),
    ("mart_compliance_exceptions.sql", "has_health_insurance_source_sql"),
])
def test_MAXIMAL_each_firing_check_is_gated(model, var):
    assert var in _sql(model)


def test_MAXIMAL_the_measured_behaviour_that_justified_the_gates():
    """The tamper for the gates: without them these fire on rows that carry no
    finding at all."""
    con = duckdb.connect()
    con.execute("CREATE TABLE att AS SELECT * FROM (VALUES "
                "(NULL,7),(NULL,0),(NULL,3)) t(src,calc)")
    assert con.execute(
        "SELECT COUNT(*) FROM att WHERE COALESCE(src,0) != calc"
    ).fetchone()[0] == 2
    con.execute("CREATE TABLE comp AS SELECT * FROM (VALUES "
                "(NULL),(NULL),(NULL)) t(status)")
    assert con.execute(
        "SELECT COUNT(*) FROM comp WHERE status IS NULL OR status != 'Active'"
    ).fetchone()[0] == 3
    con.close()


def test_SAFE_the_or_chain_ratio_is_unaffected_by_a_null():
    """Checked rather than assumed, because the payroll cycle established the
    opposite reflex. COUNT(CASE..) skips NULL and FALSE alike."""
    con = duckdb.connect()
    q = ("SELECT COUNT(CASE WHEN late>0 OR punch>0 OR absence>0 THEN 1 END), "
         "COUNT(absence) FROM ")
    con.execute("CREATE TABLE n AS SELECT * FROM (VALUES "
                "(0,NULL,0.0),(5,NULL,0.0),(0,NULL,1.0)) t(late,punch,absence)")
    con.execute("CREATE TABLE z AS SELECT * FROM (VALUES "
                "(0,0,0.0),(5,0,0.0),(0,0,1.0)) t(late,punch,absence)")
    assert con.execute(q + "n").fetchone() == con.execute(q + "z").fetchone()
    con.close()


# --------------------------------------------------------------------------
# the two inversions
# --------------------------------------------------------------------------

def test_attendance_inversion_is_corrected():
    """A biometric terminal produces punches; a schedule needs a rostering
    system. The contract also required missing_punch_count while treating the
    punches it derives from as optional - incoherent, not merely backwards."""
    required = cs.required_columns("attendance")
    assert "actual_check_in" in required and "actual_check_out" in required
    assert "scheduled_start" not in required
    assert "scheduled_end" not in required


def test_the_punches_are_required_BECAUSE_a_derivation_reads_them():
    spec = next(c for c in cs.columns("attendance")
                if c["name"] == "missing_punch_count")
    for source in der.source_columns(spec):
        assert source in cs.required_columns("attendance"), source


def test_compliance_platform_statuses_are_optional():
    required = cs.required_columns("compliance")
    for column in ("qiwa_status", "mudad_status", "health_insurance_status"):
        assert column not in required, column


def test_iqama_expiry_stays_optional_and_the_shape_question_is_untouched():
    """Relaxing three statuses does not pre-empt A5: a client using only Qiwa
    cannot supply Mudad status whatever file it arrives in."""
    assert "iqama_expiry" not in cs.required_columns("compliance")
    assert "employee_id" in cs.required_columns("compliance")
    assert "period" in cs.required_columns("compliance")
