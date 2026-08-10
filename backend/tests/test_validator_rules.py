"""Tests for the cycle 1b-i validator rules.

Under backend/tests/ because that is the only path pytest collects
(pytest.ini testpaths).

All fixtures are synthetic. Nothing here touches data/sample or data/raw.
"""
import datetime
import io
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
from validate_schema import (  # noqa: E402
    SEVERITY_EXCEPTION,
    SEVERITY_REJECT,
    SchemaValidationError,
    validate_csv,
    validate_csv_against_contract,
)

CONTRACTS = os.path.join(_ROOT, "data", "contracts")
TODAY = datetime.date(2026, 8, 10)   # pinned so the DATE upper bound is stable


def _row_for(table, overrides=None, drop=None):
    """A conformant row for `table`, with optional overrides / dropped columns."""
    overrides = overrides or {}
    drop = set(drop or [])
    names, values = [], []
    for c in cs.columns(table, CONTRACTS):
        n = c["name"]
        if n in drop:
            continue
        names.append(n)
        if n in overrides:
            values.append(str(overrides[n]))
            continue
        if c.get("allowed_values"):
            values.append(c["allowed_values"][0])
        else:
            values.append({"DATE": "2026-06-01", "TIMESTAMP": "2026-06-01 08:00:00",
                           "BOOLEAN": "true", "INTEGER": "1",
                           "DECIMAL": "1.5"}.get(str(c.get("type", "VARCHAR")).upper(), "X1"))
    return names, values


def _write(tmp_path, table, rows, drop=None, overrides_list=None):
    names, _ = _row_for(table, drop=drop)
    body = [",".join(names)]
    for i in range(rows):
        ov = (overrides_list or [{}] * rows)[i]
        _, vals = _row_for(table, overrides=ov, drop=drop)
        body.append(",".join(vals))
    p = tmp_path / "{}.csv".format(table)
    io.open(str(p), "w", encoding="utf-8", newline="").write("\n".join(body) + "\n")
    return str(p)


def _check(path, table):
    return validate_csv(path, table, contracts_dir=CONTRACTS, today=TODAY)


# --------------------------------------------------------------------------
# Rule: min_value  -> EXCEPTION (file still loads)
# --------------------------------------------------------------------------

def test_min_value_is_an_exception_not_a_rejection(tmp_path):
    p = _write(tmp_path, "payroll", 2,
               overrides_list=[{"employee_id": "E1"},
                               {"employee_id": "E2", "net_pay": "-500"}])
    r = _check(p, "payroll")
    assert r.ok, "a negative salary must NOT reject the file"
    assert len(r.exceptions) == 1
    v = r.exceptions[0]
    assert v.severity == SEVERITY_EXCEPTION
    assert v.rule == "min-value"
    assert v.row == 3, "row 1 is the header, so the second data row is row 3"
    assert "below the minimum" in v.message_en
    assert "الحد الأدنى" in v.message_ar


def test_min_value_does_not_block_the_legacy_gate(tmp_path):
    p = _write(tmp_path, "payroll", 1, overrides_list=[{"net_pay": "-1"}])
    validate_csv_against_contract(p, "payroll", contracts_dir=CONTRACTS, today=TODAY)


# --------------------------------------------------------------------------
# Rule: unique  -> REJECT on a primary key
# --------------------------------------------------------------------------

def test_duplicate_primary_key_rejects(tmp_path):
    p = _write(tmp_path, "employees", 2,
               overrides_list=[{"employee_id": "EMP001"}, {"employee_id": "EMP001"}])
    r = _check(p, "employees")
    assert not r.ok
    v = [x for x in r.rejects if x.rule == "unique-primary-key"]
    assert len(v) == 1
    assert v[0].severity == SEVERITY_REJECT
    assert "appears 2 times" in v[0].message_en
    assert "rows [2, 3]" in v[0].message_en
    assert "مكررة" in v[0].message_ar


def test_distinct_primary_keys_pass(tmp_path):
    p = _write(tmp_path, "employees", 2,
               overrides_list=[{"employee_id": "EMP001"}, {"employee_id": "EMP002"}])
    assert _check(p, "employees").ok


# --------------------------------------------------------------------------
# Rule: DATE plausible range
# --------------------------------------------------------------------------

def test_corrupted_date_serial_is_rejected(tmp_path):
    # The exact corruption named in PRODUCT-ARCHITECTURE.md §4. It parses
    # cleanly as year 25 and passed every check before this cycle.
    p = _write(tmp_path, "employees", 1, overrides_list=[{"joining_date": "0025-01-26"}])
    r = _check(p, "employees")
    assert not r.ok
    v = [x for x in r.rejects if x.rule == "date-range"]
    assert len(v) == 1
    assert v[0].row == 2
    assert "outside the plausible range" in v[0].message_en
    assert "corrupted" in v[0].message_en
    assert "خارج النطاق المعقول" in v[0].message_ar


def test_future_joining_date_is_accepted(tmp_path):
    # An accepted offer starting next month is routine and must not be blocked.
    nxt = (TODAY + datetime.timedelta(days=30)).isoformat()
    p = _write(tmp_path, "employees", 1, overrides_list=[{"joining_date": nxt}])
    assert _check(p, "employees").ok


def test_date_far_in_the_future_is_rejected(tmp_path):
    far = datetime.date(TODAY.year + 5, 1, 1).isoformat()
    p = _write(tmp_path, "employees", 1, overrides_list=[{"joining_date": far}])
    assert not _check(p, "employees").ok


def test_date_before_1940_is_rejected(tmp_path):
    p = _write(tmp_path, "employees", 1, overrides_list=[{"joining_date": "1939-12-31"}])
    assert not _check(p, "employees").ok


# --------------------------------------------------------------------------
# Rule: required_when
# --------------------------------------------------------------------------

def test_end_of_service_required_when_terminated(tmp_path):
    p = _write(tmp_path, "employees", 1,
               overrides_list=[{"status": "Terminated", "end_of_service_type": ""}])
    r = _check(p, "employees")
    assert not r.ok
    v = [x for x in r.rejects if x.rule == "required-when"]
    assert len(v) == 1
    assert v[0].row == 2
    assert "is required when" in v[0].message_en
    assert "مطلوب عندما" in v[0].message_ar


def test_end_of_service_present_when_terminated_passes(tmp_path):
    p = _write(tmp_path, "employees", 1,
               overrides_list=[{"status": "Terminated",
                                "end_of_service_type": "Resignation"}])
    assert _check(p, "employees").ok


def test_end_of_service_not_required_when_active(tmp_path):
    p = _write(tmp_path, "employees", 1,
               overrides_list=[{"status": "Active", "end_of_service_type": ""}])
    assert _check(p, "employees").ok


# --------------------------------------------------------------------------
# Rule: is_saudi derived / optional
# --------------------------------------------------------------------------

def test_file_without_is_saudi_now_validates(tmp_path):
    p = _write(tmp_path, "employees", 1, drop=["is_saudi"])
    assert _check(p, "employees").ok, "is_saudi is derived; its absence must not reject"


# --------------------------------------------------------------------------
# Structural behaviour preserved
# --------------------------------------------------------------------------

def test_unexpected_column_still_rejects(tmp_path):
    names, vals = _row_for("employees")
    p = tmp_path / "e.csv"
    io.open(str(p), "w", encoding="utf-8", newline="").write(
        ",".join(names + ["surprise"]) + "\n" + ",".join(vals + ["Z"]) + "\n")
    with pytest.raises(SchemaValidationError):
        validate_csv_against_contract(str(p), "employees",
                                      contracts_dir=CONTRACTS, today=TODAY)


def test_structural_failure_short_circuits_per_cell_checks(tmp_path):
    """A wrong-shaped file reports the shape problem alone."""
    names, vals = _row_for("employees", overrides={"joining_date": "0025-01-26"})
    p = tmp_path / "e.csv"
    io.open(str(p), "w", encoding="utf-8", newline="").write(
        ",".join(names + ["surprise"]) + "\n" + ",".join(vals + ["Z"]) + "\n")
    r = _check(str(p), "employees")
    assert [v.rule for v in r.violations] == ["no-unexpected-columns"]


def test_health_insurance_status_is_the_canonical_name():
    names = cs.column_names("compliance", CONTRACTS)
    assert "health_insurance_status" in names
    assert "insurance_status" not in names
    assert "gosi_status" in names, "the GOSI side must remain distinct"
