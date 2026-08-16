# -*- coding: utf-8 -*-
"""Mapping cycle B: attribution, affirmation, the ladder, evidence, the CLI.

Cycle A left two gaps. This suite is the enforcement for both.

  ATTRIBUTION. save_version accepted a version with no created_by, so the
  decision that turns a client's word into a canonical one could be anonymous.

  AFFIRMATION. A value mapping into a REJECT enum was applied silently. Mapping
  "معلق" (suspended) to Active counts that employee as employed in headcount,
  Saudization and payroll exposure, and nothing downstream can question it
  because data/raw is canonical by then.

What is deliberately NOT enforced is pinned here too: the eleven
EXCEPTION-severity enum columns take no affirmation. That is a decision - see
docs/phase-2/mapping-ui-plan.md §1.4 - not an oversight, and a test that says
so is the only way it stays one.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import canonical_schema as cs  # noqa: E402
import mapping  # noqa: E402
from test_mapping_profiles import a_client_export, a_profile, label_ar  # noqa: E402


@pytest.fixture(autouse=True)
def _at_root(monkeypatch):
    monkeypatch.chdir(_ROOT)


@pytest.fixture
def profile_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "PROFILE_DIR", str(tmp_path))
    monkeypatch.setattr(mapping, "CONTAINER_PROFILE_DIR", str(tmp_path))
    return tmp_path / "employees.yml"


def _version(**over):
    """A minimal saveable version: one column, its evidence, attributed."""
    header = label_ar("employees", "employee_id")
    version = {
        "created_by": "operator@synthetic.local",
        "columns": {header: "employee_id"},
        "evidence": [{"source_header": header, "chosen": "employee_id",
                      "decision": "mapped", "matched_by": "label_exact",
                      "confidence": 0.95, "rejected": [],
                      "value_profile": {"kind": "redacted", "dtype": "string",
                                        "cardinality": 3,
                                        "length_range": [6, 6],
                                        "pattern": "AAA999"}}],
    }
    version.update(over)
    return version


# --------------------------------------------------------------------------
# (a) attribution
# --------------------------------------------------------------------------

def test_a_version_without_created_by_is_REFUSED(profile_file):
    version = _version()
    version.pop("created_by")
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees", version, path=str(profile_file))
    assert "created_by" in str(excinfo.value)
    assert not profile_file.exists(), "nothing may be written on refusal"


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_a_blank_created_by_does_not_count(profile_file, blank):
    with pytest.raises(mapping.MappingError):
        mapping.save_version("employees", _version(created_by=blank),
                             path=str(profile_file))


def test_an_attributed_version_saves_and_keeps_the_name(profile_file):
    saved = mapping.save_version("employees", _version(), path=str(profile_file))
    assert saved["created_by"] == "operator@synthetic.local"
    assert saved["created_at"], "the timestamp is stamped, not supplied"


# --------------------------------------------------------------------------
# (b) affirmation - keyed by the PAIR, enforced at save AND at load
# --------------------------------------------------------------------------

def _with_values(pairs, affirmed=None, who="operator@synthetic.local"):
    version = _version(values={"status": dict(pairs)})
    if affirmed is not None:
        version["confirmations"] = {
            "status": {"confirmed_by": who, "confirmed_at": "2026-08-12T09:00:00",
                       "pairs": dict(affirmed)}}
    return version


def test_an_unaffirmed_reject_enum_mapping_is_REFUSED_at_save(profile_file):
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees", _with_values({"معلق": "Active"}),
                             path=str(profile_file))
    message = str(excinfo.value)
    assert "معلق" in message, "the operator must see which pair is unaffirmed"
    assert "Saudization" in message, "and what the mapping decides"
    assert not profile_file.exists()


def test_an_unaffirmed_mapping_is_also_REFUSED_at_LOAD(profile_file, monkeypatch):
    """Save-side alone would leave the hand-written YAML path open, and hand
    written YAML is exactly the path that produced this gap."""
    monkeypatch.setattr(mapping, "assert_value_mappings_confirmed",
                        lambda *a, **k: True)
    mapping.save_version("employees", _with_values({"معلق": "Active"}),
                         path=str(profile_file))
    monkeypatch.undo()
    assert profile_file.exists(), "it reached the disk some other way"
    with pytest.raises(mapping.MappingError):
        mapping.load_profile("employees", path=str(profile_file))


def test_an_affirmed_mapping_saves_and_loads(profile_file):
    pairs = {"معلق": "Terminated"}
    mapping.save_version("employees", _with_values(pairs, affirmed=pairs),
                         path=str(profile_file))
    loaded = mapping.load_profile("employees", path=str(profile_file))
    assert loaded["values"]["status"] == pairs
    assert loaded["confirmations"]["status"]["confirmed_by"]


def test_adding_a_pair_invalidates_the_earlier_affirmation(profile_file):
    """The whole reason it is keyed by the pair. A tick given in August must
    not silently bless a word that first appeared in September."""
    august = {"نشط": "Active"}
    september = {"نشط": "Active", "منتهي": "Terminated"}
    mapping.save_version("employees", _with_values(august, affirmed=august),
                         path=str(profile_file))
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees",
                             _with_values(september, affirmed=august),
                             path=str(profile_file))
    assert "منتهي" in str(excinfo.value)
    assert "نشط" not in str(excinfo.value), "only the new pair is at issue"


def test_a_changed_target_invalidates_it_too(profile_file):
    with pytest.raises(mapping.MappingError):
        mapping.save_version(
            "employees",
            _with_values({"معلق": "Terminated"}, affirmed={"معلق": "Active"}),
            path=str(profile_file))


def test_an_affirmation_without_a_name_does_not_count(profile_file):
    pairs = {"معلق": "Active"}
    with pytest.raises(mapping.MappingError):
        mapping.save_version("employees",
                             _with_values(pairs, affirmed=pairs, who=""),
                             path=str(profile_file))


def test_a_withdrawn_mapping_leaves_a_harmless_affirmation(profile_file):
    """confirmations may outlive the pairs they affirmed; the reverse blocks."""
    version = _version(values={"status": {"نشط": "Active"}})
    version["confirmations"] = {"status": {
        "confirmed_by": "operator@synthetic.local",
        "pairs": {"نشط": "Active", "موقوف": "Inactive"}}}
    assert mapping.save_version("employees", version, path=str(profile_file))


def test_the_three_gated_columns_are_the_reject_enums():
    gated = {"{}.{}".format(t, c)
             for t in cs.available_tables()
             for c in mapping.reject_enum_columns(t)}
    assert gated == {"employees.status", "employees.end_of_service_type",
                     "employee_relations.case_type"}


def test_an_EXCEPTION_enum_mapping_needs_NO_affirmation(profile_file):
    """PINNED AS A DECISION, NOT AN OVERSIGHT (plan §1.4).

    Eleven columns take no affirmation. Extending the gate to all fourteen
    would make the tick a formality, which is worse than not having one. So a
    mis-mapped `contract_type` remains an operator assertion the system
    accepts, and this test exists so nobody reads that as an accident.
    """
    version = _version(values={"contract_type": {"محدد": "Limited"}})
    assert mapping.save_version("employees", version, path=str(profile_file))


def test_the_consequence_text_names_what_is_at_stake():
    article_80 = mapping.consequence("employees", "end_of_service_type")
    assert "Article 80" in article_80
    assert "owed money" in article_80
    assert mapping.consequence("employees", "end_of_service_type", "ar")
    assert mapping.consequence("employees", "employment_type") is None


def test_the_consequence_text_covers_the_Unspecified_case():
    """`Unspecified` is a DIFFERENT assertion from the article-bearing values.

    The article values assert WHICH entitlement applies. `Unspecified` asserts
    that the source did not record the grounds, so NONE can be derived. An
    operator ticking the affirmation box needs to be told which of those two
    things they are doing - the original text enumerated only outcomes that
    all carry an entitlement decision, so it was incomplete the moment
    `Unspecified` was added to the enum.

    Pinned in BOTH locales, because the affirmation is shown in whichever the
    operator is working in.
    """
    for locale in ("en", "ar"):
        text = mapping.consequence("employees", "end_of_service_type", locale)
        assert "Unspecified" in text, locale
    english = mapping.consequence("employees", "end_of_service_type")
    assert "NO entitlement can be derived" in english
    assert "never as a default" in english, (
        "the text must warn against using it for a value not looked up")


# --------------------------------------------------------------------------
# the suggestion ladder
# --------------------------------------------------------------------------

def _top(table, header):
    candidates = mapping.suggest(table, [header])[header]
    return candidates[0] if candidates else None


def test_rung_1_the_canonical_key():
    assert _top("employees", "employee_id") == {
        "canonical": "employee_id", "matched_by": "canonical", "confidence": 1.0}


def test_rung_2_the_contracts_own_arabic_label():
    best = _top("employees", label_ar("employees", "nationality"))
    assert (best["canonical"], best["matched_by"]) == ("nationality", "label_exact")


def test_rung_3_absorbs_arabic_variation():
    """الجنسيه with ta-marbuta -> ha, which is the commonest real variant."""
    best = _top("employees", "الجنسيه")
    assert (best["canonical"], best["matched_by"]) == (
        "nationality", "label_normalised")
    assert _top("employees", " الجنسية ")["canonical"] == "nationality"


def test_rung_4_the_alias_table():
    best = _top("employees", "الاسم الكامل")
    assert (best["canonical"], best["matched_by"]) == ("employee_name", "alias")


def test_rung_5_is_nothing_rather_than_a_guess():
    assert mapping.suggest("employees", ["ملاحظات"])["ملاحظات"] == []


def test_aliases_are_scoped_per_table():
    """الحالة is status on employees and request_status on hr_requests. A
    global alias table would have to pick one and be wrong on the other."""
    assert _top("employees", "الحالة")["canonical"] == "status"
    assert _top("hr_requests", "الحالة")["canonical"] == "request_status"


def test_every_alias_target_exists_on_its_contract():
    aliases = mapping.load_aliases()
    for table, targets in aliases.items():
        known = {c["name"] for c in cs.columns(table)}
        assert not set(targets) - known, (table, sorted(set(targets) - known))


def test_every_candidate_carries_its_provenance():
    ranked = mapping.suggest("employees", list(a_client_export().columns))
    for header, candidates in ranked.items():
        for candidate in candidates:
            assert candidate["matched_by"], header
            assert candidate["confidence"] is not None, header


# --------------------------------------------------------------------------
# evidence by construction
# --------------------------------------------------------------------------

def _decisions(frame):
    profile = a_profile()
    out = {h: {"decision": "mapped", "chosen": c}
           for h, c in profile["columns"].items()}
    for entry in profile["ignored"]:
        out[entry["header"]] = {"decision": "ignored", "reason": entry["reason"]}
    return out


def test_build_version_covers_every_header_including_the_undecided():
    frame = a_client_export()
    version = mapping.build_version("employees", frame, {}, "op@x")
    covered = {e["source_header"] for e in version["evidence"]}
    assert covered == set(frame.columns)
    assert all(e["decision"] == "undecided" for e in version["evidence"])


def test_build_version_records_the_rung_it_matched_on():
    frame = a_client_export()
    version = mapping.build_version("employees", frame, _decisions(frame), "op@x")
    by_header = {e["source_header"]: e for e in version["evidence"]}
    assert by_header["الجنسيه"]["matched_by"] == "label_normalised"
    assert by_header["الجنسيه"]["confidence"] == 0.85
    assert by_header["ملاحظات"]["decision"] == "ignored"


def test_build_version_records_what_the_human_did_NOT_take():
    """The scarcest signal in the system: a candidate that was plausible and
    wrong. It exists only if it is written at the moment of the decision."""
    frame = pl.DataFrame({"الحالة": ["نشط"]})
    version = mapping.build_version(
        "employees", frame,
        {"الحالة": {"decision": "mapped", "chosen": "employment_type"}}, "op@x")
    evidence = version["evidence"][0]
    assert evidence["matched_by"] == "human", "not what the ladder proposed"
    assert [r["canonical"] for r in evidence["rejected"]] == ["status"]


def test_build_version_stamps_the_fingerprint():
    frame = a_client_export()
    version = mapping.build_version("employees", frame, {}, "op@x")
    assert version["source_fingerprint"] == mapping.header_fingerprint(frame.columns)


def test_a_version_with_holes_in_its_evidence_is_REFUSED(profile_file):
    version = _version()
    version["columns"]["ملاحظات"] = "job_title"     # referenced, no evidence
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees", version, path=str(profile_file))
    assert "ملاحظات" in str(excinfo.value)
    assert "build_version" in str(excinfo.value), "say how to fix it"


def test_build_version_output_saves_unchanged(profile_file):
    frame = a_client_export()
    version = mapping.build_version("employees", frame, _decisions(frame), "op@x")
    saved = mapping.save_version("employees", version, path=str(profile_file))
    assert saved["version"] == 1


def test_build_version_still_obeys_the_PII_rule(profile_file):
    frame = a_client_export()
    version = mapping.build_version("employees", frame, _decisions(frame), "op@x")
    mapping.save_version("employees", version, path=str(profile_file))
    written = profile_file.read_text(encoding="utf-8")
    assert "نشط" in written, "a vocabulary IS the signal"
    assert "X1" not in written, "a name is not"
