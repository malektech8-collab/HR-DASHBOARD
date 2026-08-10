"""Cycle 1b-ii: contract violations must reach the Data Quality layer.

Without this plumbing the EXCEPTION severity introduced in 1b-i is functionally
"ignore", which is worse than REJECT because it is silent.

All fixtures synthetic. Nothing here touches data/sample or data/raw.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import ingest_raw  # noqa: E402
import validate_data  # noqa: E402
from validate_schema import (  # noqa: E402
    DQ_SEVERITIES,
    SEVERITY_EXCEPTION,
    Violation,
    dq_recommended_action,
    dq_severity,
)


def _violation(rule="min-value", column="net_pay", table="payroll", row=7):
    return Violation(rule, table, column, SEVERITY_EXCEPTION,
                     "Row {}, Net Pay: value -500 is below the minimum of 0.".format(row),
                     "الصف {}، صافي الراتب: القيمة -500 أقل من الحد الأدنى 0.".format(row),
                     row=row, value="-500")


# --------------------------------------------------------------------------
# severity must land in the vocabulary the marts understand
# --------------------------------------------------------------------------

def test_severity_never_leaks_a_raw_validator_string():
    """base_command_center_exception_sources normalises anything outside
    Critical/Warning/Info to 'Unknown'. A raw 'exception' would render as
    Unknown on the Command Center."""
    for rule, col in [("min-value", "net_pay"), ("min-value", "late_minutes"),
                      ("unique", "case_id"), ("unique-primary-key", "employee_id"),
                      ("allowed-values", "payroll_status"), ("something-new", "x")]:
        sev = dq_severity(_violation(rule=rule, column=col))
        assert sev in DQ_SEVERITIES, "{}/{} produced {!r}".format(rule, col, sev)
        assert sev not in ("exception", "reject")


def test_negative_pay_is_critical_but_late_minutes_is_not():
    assert dq_severity(_violation(column="net_pay")) == "Critical"
    assert dq_severity(_violation(column="late_minutes", table="attendance")) == "Warning"


def test_recommended_action_is_bilingual():
    v = _violation()
    assert dq_recommended_action(v, "en") != dq_recommended_action(v, "ar")
    assert "أعد الرفع" in dq_recommended_action(v, "ar")


# --------------------------------------------------------------------------
# shape: mergeable with the gold DQ report, no invented identifiers
# --------------------------------------------------------------------------

def test_written_rows_match_the_gold_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(_ROOT)
    out = tmp_path / "contract_exceptions.parquet"
    monkeypatch.setattr(ingest_raw, "CONTRACT_EXCEPTIONS_PATH", str(out))
    ingest_raw._write_contract_exceptions([_violation()])

    df = pl.read_parquet(str(out))
    assert list(df.columns) == list(validate_data.GOLD_SCHEMA), \
        "must be mergeable with the gold report without reshaping"
    assert df.height == 1
    r = df.row(0, named=True)
    assert r["severity"] in DQ_SEVERITIES
    assert r["source"] == "contract"
    assert r["source_table"] == "payroll"
    assert r["source_row"] == 7
    assert r["source_column"] == "net_pay"
    assert r["rule"] == "min-value"
    assert r["issue_type"] == "Contract: min-value"


def test_unattributable_rows_never_invent_an_employee_id(tmp_path, monkeypatch):
    monkeypatch.chdir(_ROOT)
    out = tmp_path / "c.parquet"
    monkeypatch.setattr(ingest_raw, "CONTRACT_EXCEPTIONS_PATH", str(out))
    ingest_raw._write_contract_exceptions([_violation()])
    r = pl.read_parquet(str(out)).row(0, named=True)
    assert r["employee_id"] == ""
    assert r["employee_name"] == "Unknown"


# --------------------------------------------------------------------------
# the staleness guard
# --------------------------------------------------------------------------

def test_transport_file_is_cleared_at_the_start_of_every_run(monkeypatch, tmp_path):
    """The .uploaded marker bug in a new costume.

    A stale transport file would resurrect exceptions against data that has
    since been fixed, and a demo run would inherit a previous real run's
    exceptions. It must be unlinked at the start of EVERY run, in EVERY mode,
    before anything decides whether to write it.
    """
    monkeypatch.chdir(_ROOT)
    path = ingest_raw.CONTRACT_EXCEPTIONS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # A leftover from a previous (real) run.
    pl.DataFrame({"employee_id": ["STALE"]}).write_parquet(path)
    assert os.path.exists(path)

    # A demo run must clear it even though demo never writes one.
    ingest_raw.ingest(data_mode="demo")
    assert not os.path.exists(path), \
        "stale contract exceptions survived a demo run"


def test_demo_mode_produces_no_transport_file(monkeypatch):
    monkeypatch.chdir(_ROOT)
    ingest_raw.ingest(data_mode="demo")
    assert not os.path.exists(ingest_raw.CONTRACT_EXCEPTIONS_PATH)


# --------------------------------------------------------------------------
# the merge
# --------------------------------------------------------------------------

def test_validate_merges_contract_exceptions_into_gold(monkeypatch):
    monkeypatch.chdir(_ROOT)
    path = validate_data.CONTRACT_EXCEPTIONS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    validate_data.validate()
    before = pl.read_parquet("data/gold/data_quality_report.parquet").height

    ingest_raw._write_contract_exceptions([_violation(), _violation(row=9)])
    try:
        validate_data.validate()
        after = pl.read_parquet("data/gold/data_quality_report.parquet")
        assert after.height == before + 2
        contract_rows = after.filter(pl.col("source") == "contract")
        assert contract_rows.height == 2
        assert set(contract_rows["severity"].to_list()) <= set(DQ_SEVERITIES)
    finally:
        if os.path.exists(path):
            os.remove(path)
        validate_data.validate()   # restore demo gold


def test_gold_keeps_the_six_columns_the_marts_select():
    """mart_data_quality_exceptions selects these explicitly; the additive
    provenance columns must not disturb them."""
    for col in ("employee_id", "employee_name", "issue_type", "description",
                "severity", "recommended_action"):
        assert col in validate_data.GOLD_SCHEMA
    assert list(validate_data.GOLD_SCHEMA)[:6] == [
        "employee_id", "employee_name", "issue_type", "description",
        "severity", "recommended_action"]
