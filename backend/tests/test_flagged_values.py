# -*- coding: utf-8 -*-
"""`flag_values`: a value that is LEGAL but INCOMPLETE.

WHAT IT EXISTS FOR. A real HRIS export records the end-of-service reason as
Arabic prose that usually cites the Labor Law article. One phrase cites none:
the employer ended the contract, and the grounds were not written down.
Employer-initiated termination spans at least three outcomes that differ in
whether an award is owed, so mapping it to any article would assert an
entitlement the data does not support - and the fabricated number would be
somebody's terminal payment.

`Unspecified` is the honest canonical value. But once it is in
`allowed_values`, Rule 4 is silent on it by construction, and leavers with an
unknown end-of-service basis would commit without a word. That silence is the
defect this rule removes.

Per SP-001 every assertion here is paired with a tamper: the rule is watched
FAILING to fire when it should not, and firing when it should.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
import validate_schema as vs  # noqa: E402

COLUMN = "end_of_service_type"


def _row(employee_id, eos_type, status="Terminated"):
    row = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name == "employee_id":
            row[name] = employee_id
        elif name == COLUMN:
            row[name] = eos_type
        elif name == "status":
            row[name] = status
        elif name == "is_saudi":
            row[name] = "true"
        elif name == "joining_date":
            row[name] = "2024-01-15"
        elif name in ("termination_date", "contract_end_date"):
            row[name] = "2026-01-31"
        elif spec.get("allowed_values"):
            row[name] = spec["allowed_values"][0]
        elif str(spec.get("type", "")).upper() == "DECIMAL":
            row[name] = "5000"
        else:
            row[name] = "PLACEHOLDER"
    return row


@pytest.fixture
def validate(tmp_path):
    def _run(rows):
        path = tmp_path / "employees.csv"
        pl.DataFrame(rows).write_csv(str(path))
        return vs.validate_csv(str(path), "employees")
    return _run


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------

def test_unspecified_is_an_allowed_value():
    spec = next(c for c in cs.columns("employees") if c["name"] == COLUMN)
    assert "Unspecified" in spec["allowed_values"]


def test_it_carries_a_bilingual_label_naming_the_ABSENCE():
    spec = next(c for c in cs.columns("employees") if c["name"] == COLUMN)
    label = spec["value_labels"]["Unspecified"]
    assert "grounds not recorded" in label["en"]
    # The Arabic says the grounds were not RECORDED, not merely that the type
    # is unspecified - a bare "غير محدد" reads as a shrug.
    assert "لم يُسجَّل" in label["ar"]


def test_the_column_description_warns_a_future_mart_author():
    """The forward note lives where someone building a leavers mart will meet
    it - on the column itself, not only in a plan document."""
    spec = next(c for c in cs.columns("employees") if c["name"] == COLUMN)
    description = spec["description_en"]
    assert "eighth category" in description
    assert "COALESCE(project, 'Unassigned')" in description
    assert "coverage note" in description


# --------------------------------------------------------------------------
# the rule fires - and the file still loads
# --------------------------------------------------------------------------

def test_unspecified_does_NOT_reject_the_file(validate):
    """The whole point: the grounds do not exist to supply, so refusing the
    file would leave the client only a fabrication as a route in."""
    result = validate([_row("E1", "Unspecified")])
    assert result.rejects == []


def test_unspecified_raises_an_EXCEPTION(validate):
    result = validate([_row("E1", "Unspecified")])
    assert len(result.exceptions) == 1
    assert result.exceptions[0].rule == "flagged-value"
    assert result.exceptions[0].severity == vs.SEVERITY_EXCEPTION


def test_it_names_the_ROW_not_just_the_column(validate):
    """Per row, unlike Rule 4's file-level message. The product's stated
    differentiator is telling a client WHICH records are affected."""
    result = validate([
        _row("E1", "Article 80"),
        _row("E2", "Unspecified"),
        _row("E3", "Resignation"),
        _row("E4", "Unspecified"),
    ])
    rows = sorted(v.row for v in result.exceptions if v.rule == "flagged-value")
    assert rows == [3, 5], "header is row 1, so data rows 2 and 4 are 3 and 5"


def test_the_message_is_bilingual_and_carries_the_reason(validate):
    result = validate([_row("E1", "Unspecified")])
    violation = result.exceptions[0]
    assert "grounds not recorded" in violation.message_en
    assert "No end-of-service entitlement can be derived" in violation.message_en
    assert "لم يُسجَّل" in violation.message_ar


# --------------------------------------------------------------------------
# SP-001: watch it NOT fire, so firing means something
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    "Resignation", "Article 74", "Article 75", "Article 77",
    "Article 80", "Article 81", "Probation",
])
def test_the_seven_article_bearing_values_are_NOT_flagged(validate, value):
    """If every value flagged, the flag would carry no information."""
    result = validate([_row("E1", value)])
    assert [v for v in result.exceptions if v.rule == "flagged-value"] == []
    assert result.rejects == []


def test_an_empty_value_is_not_flagged_by_this_rule(validate):
    """An active employee has no end-of-service type. That is not a gap in the
    grounds; it is the absence of a termination. `required_when` owns the
    Terminated-but-empty case and still rejects it."""
    result = validate([_row("E1", "", status="Active")])
    assert [v for v in result.exceptions if v.rule == "flagged-value"] == []


def test_terminated_with_an_EMPTY_type_still_REJECTS(validate):
    """`Unspecified` is not a licence to leave the column blank. The client
    must say "the grounds were not recorded"; they cannot say nothing."""
    result = validate([_row("E1", "", status="Terminated")])
    assert any(v.rule == "required_when" or "required" in v.rule
               for v in result.rejects), [v.rule for v in result.rejects]


def test_a_genuinely_unknown_value_still_REJECTS(validate):
    """Widening the enum by one must not have widened it to anything."""
    result = validate([_row("E1", "Article 99")])
    assert any(v.rule == "allowed-values" for v in result.rejects)


# --------------------------------------------------------------------------
# the cap - sized for a real export, not a fixture
# --------------------------------------------------------------------------

def test_the_flag_is_capped_with_a_tail(validate):
    """A client with more flagged rows than the cap must get a usable message
    and a true total, not one violation per row."""
    rows = [_row("E{}".format(i), "Unspecified")
            for i in range(vs.MAX_RENDERED_VIOLATIONS + 25)]
    result = validate(rows)
    flagged = [v for v in result.exceptions if v.rule == "flagged-value"]
    assert len(flagged) == vs.MAX_RENDERED_VIOLATIONS + 1, "capped, plus a tail"
    assert "and 25 more" in flagged[-1].message_en


# --------------------------------------------------------------------------
# the mechanism is generic, and declarative only
# --------------------------------------------------------------------------

def test_flag_values_is_declarative_and_carries_no_expression():
    """A contract is operator-supplied data. `required_when` is declarative for
    that reason and so is this: a value -> severity + bilingual reason, never
    a string to evaluate."""
    spec = next(c for c in cs.columns("employees") if c["name"] == COLUMN)
    rule = spec["flag_values"]["Unspecified"]
    assert set(rule) <= {"severity", "reason_en", "reason_ar"}
    assert rule["severity"] == "exception"


def test_the_rule_would_fire_for_any_table_and_value(tmp_path):
    """Nothing about this is end-of-service specific.

    Verified against a THROWAWAY contract so the assertion is about the
    mechanism rather than about the one contract that uses it today.
    """
    import shutil

    import yaml

    contracts = tmp_path / "contracts"
    shutil.copytree(os.path.join(_ROOT, "data", "contracts"), str(contracts))
    spec = {
        "version": 1, "table": "widgets", "label_en": "Widgets",
        "label_ar": "قطع", "description_en": "x", "description_ar": "س",
        "columns": [{
            "name": "grade", "name_en": "Grade", "name_ar": "الدرجة",
            "type": "VARCHAR", "required": True,
            "description_en": "x", "description_ar": "س", "example": "A",
            "allowed_values": ["A", "B", "Provisional"],
            "value_labels": {"Provisional": {"en": "Provisional",
                                             "ar": "مؤقت"}},
            "flag_values": {"Provisional": {
                "severity": "exception",
                "reason_en": "Not yet confirmed.",
                "reason_ar": "لم يتم التأكيد بعد."}},
        }],
    }
    with open(str(contracts / "widgets_schema.yml"), "w",
              encoding="utf-8") as handle:
        yaml.safe_dump(spec, handle, allow_unicode=True, sort_keys=False)
    path = tmp_path / "widgets.csv"
    pl.DataFrame({"grade": ["A", "Provisional"]}).write_csv(str(path))

    result = vs.validate_csv(str(path), "widgets", contracts_dir=str(contracts))
    assert result.rejects == []
    assert [v.row for v in result.exceptions if v.rule == "flagged-value"] == [3]


def test_a_reject_severity_flag_would_block(tmp_path):
    """`severity: reject` is expressible, and is watched blocking - so the
    EXCEPTION choice for Unspecified is a decision, not the only option."""
    import shutil

    import yaml

    contracts = tmp_path / "contracts"
    shutil.copytree(os.path.join(_ROOT, "data", "contracts"), str(contracts))
    spec = {
        "version": 1, "table": "widgets", "label_en": "Widgets",
        "label_ar": "قطع", "description_en": "x", "description_ar": "س",
        "columns": [{
            "name": "grade", "name_en": "Grade", "name_ar": "الدرجة",
            "type": "VARCHAR", "required": True,
            "description_en": "x", "description_ar": "س", "example": "A",
            "allowed_values": ["A", "Banned"],
            "flag_values": {"Banned": {"severity": "reject",
                                       "reason_en": "Never acceptable.",
                                       "reason_ar": "غير مقبول."}},
        }],
    }
    with open(str(contracts / "widgets_schema.yml"), "w",
              encoding="utf-8") as handle:
        yaml.safe_dump(spec, handle, allow_unicode=True, sort_keys=False)
    path = tmp_path / "widgets.csv"
    pl.DataFrame({"grade": ["Banned"]}).write_csv(str(path))

    result = vs.validate_csv(str(path), "widgets", contracts_dir=str(contracts))
    assert any(v.rule == "flagged-value" for v in result.rejects)
