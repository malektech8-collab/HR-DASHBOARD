# -*- coding: utf-8 -*-
"""Cycle B rulings 1 and 2: nationality aliases, and enum vocabularies.

Both rulings are about the same failure shape - a value the system does not
recognise, resolved by a human decision that is then invisible in the data.
These tests exist to keep each decision attached to its reason.

RULING 1. Nineteen Arabic nationality values from a real KSA export, all
non-Saudi. Two carried trailing whitespace; they are NOT added as padded
variants, because `_normalise` already strips and collapses whitespace. The
test below is what makes that claim checkable rather than asserted.

`غير سعودي` is in the table for correctness and flagged on the contract for
completeness: false is the right answer, and the nationality itself is missing.

RULING 2. The two enum vocabularies map to the CONTRACT's strings. The plain
reading of مدة محددة / غير محددة is Fixed-term / Indefinite; the contract says
Limited / Unlimited. Nothing in the code said so until this cycle.

Per SP-001 each assertion is paired with a tamper - the behaviour is watched
NOT firing as well as firing.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
import derivations as der  # noqa: E402
import mapping  # noqa: E402
import validate_schema as vs  # noqa: E402
from text import _normalise  # noqa: E402

# The nineteen, verbatim from the export - including the two with trailing
# whitespace, which are left exactly as they arrived.
UNRECOGNISED = [
    "الأوزبكستاني", "البوسنية", "البولندي", "الغاني", "الكيني", "برتغالي",
    "بريطاني", "بنجلاديش", "تركي", "جنوب افريقي", "جيبوتي", "دومينيكا",
    "روسي", "صومالي ", "غيانا", "غير سعودي", "غينيا", "فلسطيني", "نيبالي ",
]
PADDED = ["صومالي ", "نيبالي "]
CATEGORY_NOT_A_NATIONALITY = "غير سعودي"


# --------------------------------------------------------------------------
# ruling 1 - the aliases
# --------------------------------------------------------------------------

def test_all_nineteen_resolve_and_every_one_is_non_saudi():
    assert der.nationality_is_saudi(UNRECOGNISED) == [False] * 19


def test_the_guard_still_refuses_a_value_nobody_ruled_on():
    """The tamper. Adding nineteen values must not have widened the rule into
    a default - an unrecognised nationality still stops the load."""
    with pytest.raises(der.DerivationError) as exc:
        der.nationality_is_saudi(["Martian"])
    assert "Martian" in str(exc.value)
    assert "Refusing to guess" in str(exc.value)


def test_saudi_is_still_saudi():
    assert der.nationality_is_saudi(["سعودي", "Saudi", "سعوديه"]) == [True] * 3


# --------------------------------------------------------------------------
# ruling 1 - whitespace belongs at NORMALISATION, not in the table
# --------------------------------------------------------------------------

def test_padded_values_resolve_although_no_padded_alias_exists():
    assert der.nationality_is_saudi(PADDED) == [False, False]
    for value in PADDED:
        assert value not in der._NON_SAUDI_ALIASES       # the padded form
        assert value.strip() in der._NON_SAUDI_ALIASES   # only the bare one


def test_the_normaliser_is_what_absorbs_the_padding():
    """The tamper, one layer down. If `_normalise` ever stops stripping, the
    test above would start passing for the wrong reason - the padded string
    would have to be in the table. This watches the mechanism itself."""
    for value in PADDED:
        assert _normalise(value) == _normalise(value.strip())
        assert _normalise(value) == value.strip()


# --------------------------------------------------------------------------
# ruling 1 - غير سعودي is a category, and the client is told so
# --------------------------------------------------------------------------

def _row(employee_id, nationality):
    row = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name == "employee_id":
            row[name] = employee_id
        elif name == "nationality":
            row[name] = nationality
        elif name == "is_saudi":
            row[name] = "false"
        elif name == "joining_date":
            row[name] = "2024-01-15"
        elif name in ("termination_date", "contract_end_date"):
            row[name] = "2026-01-31"
        elif spec.get("allowed_values"):
            row[name] = spec["allowed_values"][0]
        elif str(spec.get("type", "")).upper() in ("DATE", "TIMESTAMP"):
            # A DATE column cannot take "PLACEHOLDER" - it fails
            # type-conformance. Added when iqama_expiry moved onto the
            # employees contract and every generic fixture in the suite went
            # red at once.
            row[name] = "2026-01-01"
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


def test_the_category_is_flagged_as_an_EXCEPTION_not_a_reject(validate):
    """It must not block. The client cannot supply a nationality their source
    never recorded, so refusing the file leaves only invention as a route in.
    """
    result = validate([_row("E1", CATEGORY_NOT_A_NATIONALITY)])
    assert result.rejects == []
    flagged = [v for v in result.exceptions if v.rule == "flagged-value"
               and v.column == "nationality"]
    assert len(flagged) == 1


def test_the_message_says_what_is_LOST_not_merely_that_it_is_odd(validate):
    result = validate([_row("E1", CATEGORY_NOT_A_NATIONALITY)])
    flagged = next(v for v in result.exceptions if v.column == "nationality")
    assert "category" in flagged.message_en
    # The consequence, in both languages: Saudization is fine, everything
    # finer than it is not.
    assert "Saudization is unaffected" in flagged.message_en
    assert "السعودة" in flagged.message_ar


def test_a_real_nationality_is_NOT_flagged(validate):
    """The tamper. A free-text column must not acquire a rule that fires on
    ordinary values - `flag_values` is exact-match for exactly this reason."""
    result = validate([_row("E1", "مصري"), _row("E2", "Saudi")])
    assert [v for v in result.exceptions if v.column == "nationality"] == []


def test_the_category_still_derives_to_false():
    """Flagging it does not change the answer. is_saudi is false, and the
    Saudization percentage computed from it stays correct."""
    assert der.nationality_is_saudi([CATEGORY_NOT_A_NATIONALITY]) == [False]


# --------------------------------------------------------------------------
# ruling 2 - the vocabularies, and the guard that now checks them
# --------------------------------------------------------------------------

RULED = {
    "employment_type": {"دوام كامل": "Full-time"},
    "contract_type": {"مدة محددة": "Limited", "غير محددة": "Unlimited"},
}


def test_every_ruled_target_is_a_contract_value():
    for column, pairs in RULED.items():
        allowed = set(next(c for c in cs.columns("employees")
                           if c["name"] == column)["allowed_values"])
        assert set(pairs.values()) <= allowed


def test_the_contract_does_NOT_use_the_plain_english_words():
    """The reason ruling 2 said to check. Fixed-term and Indefinite are the
    natural reading of the Arabic and are not what the contract calls them.
    If the contract is ever renamed to match, this test is the notice."""
    allowed = set(next(c for c in cs.columns("employees")
                       if c["name"] == "contract_type")["allowed_values"])
    assert allowed == {"Limited", "Unlimited"}
    assert "Fixed-term" not in allowed and "Indefinite" not in allowed


def _profile(values):
    return {"version": 1, "table": "employees", "columns": {},
            "ignored": [], "values": values, "derive": {}, "constants": {},
            "confirmations": {}, "evidence": []}


def test_a_value_map_to_a_non_contract_word_is_REFUSED():
    with pytest.raises(mapping.MappingError) as exc:
        mapping._validate_targets(
            "employees",
            _profile({"contract_type": {"مدة محددة": "Fixed-term"}}))
    assert "Fixed-term" in str(exc.value)
    # The message must carry the words that WOULD have worked.
    assert "Limited" in str(exc.value)


def test_the_ruled_maps_pass_that_same_guard():
    """The tamper. A guard that refused everything would pass the test above
    while making value mapping impossible."""
    assert mapping._validate_targets("employees", _profile(RULED)) is True


def test_a_free_text_column_is_left_alone_by_the_guard():
    """Second tamper: only columns with a vocabulary are constrained. A value
    map on free text - a department rename, say - has nothing to check
    against, and must not be refused for want of a list."""
    assert mapping._validate_targets(
        "employees", _profile({"department": {"مالية": "Finance"}})) is True
