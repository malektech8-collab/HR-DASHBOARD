# -*- coding: utf-8 -*-
"""A per-column date ceiling, and a message that names the right fault.

WHAT WENT WRONG. The global plausible range is 1940-01-01 .. today + 2 years.
The upper bound is right for a joining date - an accepted offer starting next
month is routine, three years out is not. It is wrong for a contract END date,
where a multi-year fixed term is ordinary in KSA and routine for senior staff.

A real export was REJECTED on exactly that, and the rejection told the client:

    "A year like 0025 usually means a corrupted Excel date serial - check the
     source export."

Every rejected date was in the FUTURE. The message sent a client hunting for a
corruption that was not in their file, and because the rule rejects, they
could not load until they found it.

TWO FIXES, and the ruling was explicit that the second alone is not enough:
splitting the message while keeping a global ceiling leaves the client blocked
with better prose. `max_years_ahead` states what is actually true per column.

Per SP-001 each assertion is paired with a tamper.
"""
import datetime
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
import validate_schema as vs  # noqa: E402

TODAY = datetime.date(2026, 8, 16)
COLUMN = "contract_end_date"


def _row(employee_id, **overrides):
    row = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name == "employee_id":
            row[name] = employee_id
        elif name == "is_saudi":
            row[name] = "true"
        elif name == "joining_date":
            row[name] = "2024-01-15"
        elif name in ("termination_date", "contract_end_date"):
            row[name] = "2027-01-31"
        elif spec.get("allowed_values"):
            row[name] = spec["allowed_values"][0]
        elif str(spec.get("type", "")).upper() == "DECIMAL":
            row[name] = "5000"
        else:
            row[name] = "PLACEHOLDER"
    row.update(overrides)
    return row


@pytest.fixture
def validate(tmp_path):
    def _run(rows):
        path = tmp_path / "employees.csv"
        pl.DataFrame(rows).write_csv(str(path))
        return vs.validate_csv(str(path), "employees", today=TODAY)
    return _run


def _date_rejects(result, column=COLUMN):
    return [x for x in result.rejects
            if x.rule == "date-range" and x.column == column]


# --------------------------------------------------------------------------
# the ceiling
# --------------------------------------------------------------------------

def test_the_contract_declares_the_wider_ceiling():
    spec = next(c for c in cs.columns("employees") if c["name"] == COLUMN)
    assert spec["max_years_ahead"] == 10


def test_a_multi_year_fixed_term_contract_LOADS(validate):
    """The case that was rejected. Six years out is an ordinary senior
    contract and is now inside the ceiling."""
    result = validate([_row("E1", contract_end_date="2032-06-30")])
    assert _date_rejects(result) == []


def test_a_date_beyond_even_the_wider_ceiling_is_still_REJECTED(validate):
    """The tamper. Raising a ceiling must not remove it - the rule still
    exists to catch corruption."""
    result = validate([_row("E1", contract_end_date="2099-01-01")])
    assert len(_date_rejects(result)) == 1


def test_the_wider_ceiling_applies_to_THIS_column_only(validate):
    """The second tamper, and the point of doing it per column. A joining date
    six years out is not plausible and must still reject - if it did not, the
    change would have loosened every date in the contract."""
    result = validate([_row("E1", joining_date="2032-06-30")])
    assert len(_date_rejects(result, "joining_date")) == 1


def test_the_floor_is_untouched(validate):
    result = validate([_row("E1", contract_end_date="0025-02-11")])
    assert len(_date_rejects(result)) == 1


# --------------------------------------------------------------------------
# the message - the two bounds have different causes
# --------------------------------------------------------------------------

def test_below_the_floor_still_blames_a_corrupted_serial(validate):
    result = validate([_row("E1", contract_end_date="0025-02-11")])
    message = _date_rejects(result)[0].message_en
    assert "corrupted Excel date serial" in message
    assert "is before 1940-01-01" in message


def test_above_the_ceiling_does_NOT_blame_a_corrupted_serial(validate):
    """The correction. This is what the real export met, and what sent a
    client looking for a fault that was not in their file."""
    result = validate([_row("E1", contract_end_date="2099-01-01")])
    message = _date_rejects(result)[0].message_en
    # It does not DIAGNOSE a corruption. A date in 2099 may well be one - the
    # rule cannot know, and the old text asserted that it did.
    assert "corrupted Excel date serial" not in message
    # It names the other possibility, which the old text never offered.
    assert "ceiling is too tight" in message
    assert "2036-08-16" in message      # the column's own ceiling, not global


def test_both_messages_are_bilingual(validate):
    for value in ("0025-02-11", "2099-01-01"):
        violation = _date_rejects(validate([_row("E1",
                                                 contract_end_date=value)]))[0]
        assert violation.message_ar.strip()
        assert violation.message_en != violation.message_ar
        assert "الصف" in violation.message_ar


def test_the_arabic_also_splits(validate):
    """A split that only reached English would leave an Arabic-reading client
    with the wrong diagnosis - which is the whole defect, untouched."""
    low = _date_rejects(validate([_row("E1",
                                       contract_end_date="0025-02-11")]))[0]
    high = _date_rejects(validate([_row("E1",
                                        contract_end_date="2099-01-01")]))[0]
    assert "Excel" in low.message_ar          # corrupted-serial text
    assert "Excel" not in high.message_ar
    assert low.message_ar != high.message_ar


# --------------------------------------------------------------------------
# the mechanism
# --------------------------------------------------------------------------

def test_years_ahead_survives_a_leap_day():
    """29 February plus ten years is not a date. The old inline construction
    would have raised inside the validator on that one day."""
    assert vs._years_ahead(datetime.date(2028, 2, 29), 10) == \
        datetime.date(2038, 2, 28)


def test_an_absolute_max_date_still_wins(monkeypatch, tmp_path):
    """Precedence, stated: `max_date` beats `max_years_ahead`. Nothing in the
    repo declares both today; this pins the order before something does."""
    columns = [dict(c) for c in cs.columns("employees")]
    for column in columns:
        if column["name"] == COLUMN:
            column["max_date"] = "2027-12-31"
    monkeypatch.setattr(vs, "_load_contract", lambda *a, **k: columns)

    path = tmp_path / "employees.csv"
    pl.DataFrame([_row("E1", contract_end_date="2032-06-30")]).write_csv(
        str(path))
    result = vs.validate_csv(str(path), "employees", today=TODAY)
    rejects = _date_rejects(result)
    assert len(rejects) == 1
    assert "2027-12-31" in rejects[0].message_en


def test_a_column_declaring_neither_keeps_the_global_ceiling(validate):
    """The compatibility line. Only one column opts in; every other date
    behaves exactly as it did."""
    declaring = [c["name"] for c in cs.columns("employees")
                 if c.get("max_years_ahead") or c.get("max_date")]
    assert declaring == [COLUMN]
    # today + 2y is 2028-08-16, so this is one day over the global ceiling.
    result = validate([_row("E1", joining_date="2028-08-17")])
    assert len(_date_rejects(result, "joining_date")) == 1
