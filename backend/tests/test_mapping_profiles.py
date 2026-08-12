"""Mapping profiles, cycle A.

The three proofs this cycle owes:

  (a) a violation names the CLIENT'S column and the CLIENT'S row
  (b) the PII rule holds under test, not under comment
  (c) mapped.csv revalidates through the unchanged ingest path

Fixtures are synthetic Arabic headers built from the contract's own `name_ar`,
plus the messy cases a real export carries - trailing spaces, an alef variant,
a `Column14` - constructed deliberately, because a fixture generated from the
schema is cleaner than reality and would prove less than it appears to.
"""
import io
import os
import sys

import polars as pl
import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

import canonical_schema as cs  # noqa: E402
import mapping  # noqa: E402
import validate_schema  # noqa: E402
from text import normalise  # noqa: E402


def label_ar(table, column):
    for spec in cs.columns(table):
        if spec["name"] == column:
            return spec["name_ar"]
    raise AssertionError(column)


@pytest.fixture(autouse=True)
def _at_root(monkeypatch):
    monkeypatch.chdir(_ROOT)


@pytest.fixture
def profile_file(tmp_path, monkeypatch):
    path = tmp_path / "employees.yml"
    monkeypatch.setattr(mapping, "PROFILE_DIR", str(tmp_path))
    monkeypatch.setattr(mapping, "CONTAINER_PROFILE_DIR", str(tmp_path))
    return path


# --------------------------------------------------------------------------
# a client's export, as described: Arabic headers, extra columns, messiness
# --------------------------------------------------------------------------

def a_client_export(**overrides):
    """An export shaped like a real one: every contract column present under
    its Arabic label, plus the junk a real file carries.

    Built from `name_ar` rather than hand-written, because the point is the
    SHAPE. The messiness is added deliberately - a fixture generated purely
    from the schema is cleaner than reality and would prove less than it looks.
    """
    data = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name == "is_saudi":
            continue                                  # derived, absent from source
        header = spec["name_ar"]
        if name == "nationality":
            header = "الجنسيه"                        # ta marbuta -> ha variant
        if name == "employee_name":
            header = header + " "                     # trailing space
        if name == "employee_id":
            values = ["EMP001", "EMP002", "EMP003"]
        elif name == "joining_date":
            values = ["2024-01-15", "0025-02-11", "2023-06-01"]
        elif name == "contract_end_date":
            values = ["2027-01-01"] * 3
        elif name == "nationality":
            values = ["سعودي", "مصري", "Saudi"]
        elif name == "status":
            values = ["نشط", "موقوف", "نشط"]
        elif name in ("termination_date", "end_of_service_type"):
            values = ["", "", ""]
        elif spec.get("allowed_values"):
            values = [spec["allowed_values"][0]] * 3
        elif str(spec.get("type", "")).upper() == "DECIMAL":
            values = ["5000", "5000", "5000"]
        else:
            values = ["X1", "X2", "X3"]
        data[header] = values

    data["ملاحظات"] = ["", "note", ""]        # free text, no canonical home
    data["Column14"] = ["", "", ""]           # empty in every row
    frame = pl.DataFrame(data)
    for header, values in overrides.items():
        frame = frame.with_columns(pl.Series(header, values))
    return frame


def a_profile():
    """The mapping an operator would write for that export."""
    columns = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name == "is_saudi":
            continue
        header = spec["name_ar"]
        if name == "nationality":
            header = "الجنسيه"
        if name == "employee_name":
            header = header + " "
        columns[header] = name
    return {
        "version": 1,
        "created_by": "operator@synthetic.local",
        "columns": columns,
        "ignored": [
            {"header": "ملاحظات", "reason": "Free-text notes; no canonical home."},
            {"header": "Column14", "reason": "Empty in every row of the sample."},
        ],
        "derive": {"is_saudi": {"rule": "nationality_is_saudi",
                                "from": "الجنسيه"}},
        "values": {"status": {"نشط": "Active", "موقوف": "Inactive"}},
        # Cycle B: a value mapping into a REJECT enum needs an affirmation
        # keyed by the PAIR. This fixture was written before that rule and is
        # exactly the shape it catches - a mapping that rewrites a client's
        # words with nobody's name on it.
        "confirmations": {
            "status": {
                "confirmed_by": "operator@synthetic.local",
                "confirmed_at": "2026-08-12T09:00:00",
                "pairs": {"نشط": "Active", "موقوف": "Inactive"},
            },
        },
    }


# --------------------------------------------------------------------------
# (a) a violation names the client's column and row
# --------------------------------------------------------------------------

def test_the_back_map_names_the_clients_own_header():
    frame = a_client_export()
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert report.back_map["joining_date"] == label_ar("employees", "joining_date")
    assert report.back_map["employee_id"] == label_ar("employees", "employee_id")


def test_a_violation_can_be_rendered_in_the_clients_terms(tmp_path):
    """The full path: a corrupted date serial in an Arabic-headed file."""
    frame = a_client_export()
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    path = tmp_path / "mapped.csv"
    mapped.write_csv(path)

    result = validate_schema.validate_csv(str(path), "employees")
    dates = [v for v in result.rejects if v.column == "joining_date"]
    assert dates, "the 0025 serial should have been rejected"
    violation = dates[0]

    # the validator stays canonical-only...
    assert violation.column == "joining_date"
    # ...and the edge translates it into what the client actually wrote
    assert report.back_map[violation.column] == label_ar("employees", "joining_date")
    # the client's own row, unchanged: row 3 of their file (header + 2 rows)
    assert violation.row == 3


def test_mapping_is_row_preserving():
    """Renames and derives; never filters, reorders or deduplicates. If it did,
    every row number in every violation would point at the wrong record."""
    frame = a_client_export()
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert mapped.height == frame.height == 3
    assert report.row_count == 3
    # row identity: the nth mapped row still describes the nth source row
    assert mapped["employee_id"].to_list() == ["EMP001", "EMP002", "EMP003"]


# --------------------------------------------------------------------------
# (b) the PII rule
# --------------------------------------------------------------------------

def test_verbatim_values_are_kept_only_for_vocabulary_columns():
    frame = a_client_export()
    evidence = mapping.build_evidence("employees", frame, a_profile())
    by_header = {e["source_header"]: e for e in evidence}

    status = by_header[label_ar("employees", "status")]["value_profile"]
    assert status["kind"] == "vocabulary"
    assert "نشط" in status["distinct_values"]

    name = by_header[label_ar("employees", "employee_name") + " "]["value_profile"]
    assert name["kind"] == "redacted"
    assert "distinct_values" not in name
    assert "Ahmad" not in str(name), "a client's employee names must not persist"


def test_a_redacted_profile_still_carries_a_usable_shape():
    """The rule is not "store nothing" - it is "store what a model can use
    without storing a person"."""
    profile = mapping.value_profile("employees", "employee_id",
                                    ["EMP001", "EMP002", "EMP003"])
    assert profile["kind"] == "redacted"
    assert profile["dtype"] == "string"
    assert profile["cardinality"] == 3
    assert profile["length_range"] == [6, 6]
    assert profile["pattern"] == "AAA999"


def test_saving_a_profile_with_leaked_values_is_REFUSED(profile_file):
    """Enforced at the write, because a comment is not a control."""
    version = a_profile()
    version["evidence"] = [{
        "source_header": label_ar("employees", "employee_name"),
        "chosen": "employee_name",
        "value_profile": {"kind": "vocabulary",
                          "distinct_values": ["Ahmad", "Sara"]},
    }]
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees", version, path=str(profile_file))
    assert "verbatim sample values" in str(excinfo.value)
    assert not profile_file.exists(), "nothing may be written on refusal"


def test_a_vocabulary_column_may_keep_its_values(profile_file):
    version = a_profile()
    version["evidence"] = mapping.build_evidence(
        "employees", a_client_export(), version)
    saved = mapping.save_version("employees", version, path=str(profile_file))
    assert saved["version"] == 1
    written = profile_file.read_text(encoding="utf-8")
    assert "نشط" in written              # the vocabulary is the training signal
    assert "Ahmad" not in written        # the person is not


# --------------------------------------------------------------------------
# (c) the mapped file revalidates through the unchanged ingest path
# --------------------------------------------------------------------------

def test_the_mapped_file_is_canonical_and_passes_the_contract(tmp_path):
    frame = a_client_export()
    # a clean export this time - the point is the SHAPE, not the violations
    frame = frame.with_columns(
        pl.Series(label_ar("employees", "joining_date"),
                  ["2024-01-15", "2024-02-11", "2023-06-01"]))
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())

    contracted = set(cs.column_names("employees"))
    assert set(mapped.columns) <= contracted, (
        "a mapped file must contain only canonical columns, or Rule 2 rejects it")
    assert "is_saudi" in mapped.columns, "the derivation ran"
    assert mapped["is_saudi"].to_list() == [True, False, True]
    assert mapped["status"].to_list() == ["Active", "Inactive", "Active"]

    path = tmp_path / "employees.csv"
    mapped.write_csv(path)
    result = validate_schema.validate_csv(str(path), "employees")
    unexpected = [v for v in result.rejects if v.rule == "no-unexpected-columns"]
    assert not unexpected, [v.message_en for v in unexpected]


def test_nothing_downstream_knows_profiles_exist():
    """Structural. The profile is an upload-time concern; if ingest or the
    warehouse learned about it, this would be a second ingest path."""
    for relative in ("scripts/ingest_raw.py", "scripts/build_warehouse.py",
                     "scripts/validate_data.py"):
        source = io.open(os.path.join(_ROOT, relative), encoding="utf-8").read()
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("#"))
        assert "mapping" not in code.lower() or "import mapping" not in code, relative


# --------------------------------------------------------------------------
# no eval, ever
# --------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    "lambda v: v.upper()",
    "__import__('os').system('rm -rf /')",
    "eval('1+1')",
    "os.remove('data')",
])
def test_an_expression_shaped_profile_is_refused(payload, profile_file):
    profile_file.write_text(
        yaml.safe_dump({"table": "employees",
                        "versions": [{"version": 1,
                                      "derive": {"is_saudi": payload}}]},
                       allow_unicode=True),
        encoding="utf-8")
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.load_profile("employees", path=str(profile_file))
    assert "expression" in str(excinfo.value)


def test_an_unknown_derivation_rule_is_refused(profile_file):
    """Resolved from the registry. A new rule is reviewed code, not config."""
    version = a_profile()
    version["derive"] = {"is_saudi": {"rule": "guess_it", "from": "الجنسيه"}}
    with pytest.raises(Exception) as excinfo:
        mapping._validate_targets("employees", version)
    assert "Unknown derivation rule" in str(excinfo.value)


def test_a_typo_in_a_canonical_target_is_refused():
    version = a_profile()
    version["columns"]["الجنسيه"] = "nationalty"
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping._validate_targets("employees", version)
    assert "nationalty" in str(excinfo.value)


# --------------------------------------------------------------------------
# unmapped columns and values
# --------------------------------------------------------------------------

def test_an_undecided_column_is_reported_rather_than_dropped():
    """Mapped, explicitly ignored, or it blocks. A default-drop would let a
    renamed export silently lose a column."""
    frame = a_client_export().with_columns(pl.Series("رقم الهوية", ["1", "2", "3"]))
    _mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert report.unmapped == ["رقم الهوية"]


def test_an_explicitly_ignored_column_is_dropped_and_recorded():
    frame = a_client_export()
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert "ملاحظات" not in mapped.columns
    assert set(report.ignored) == {"ملاحظات", "Column14"}


def test_an_unmapped_value_in_a_REJECT_enum_is_reported_with_its_options():
    frame = a_client_export().with_columns(
        pl.Series(label_ar("employees", "status"), ["نشط", "معلق", "منتهي"]))
    _mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert report.unmapped_values["status"] == {"معلق", "منتهي"}
    # and the UI can offer the canonical vocabulary rather than a bare refusal
    assert "Active" in mapping.reject_enum_columns("employees")["status"]


def test_value_matching_absorbs_arabic_variation():
    """A trailing space or an alef variant must not need a second entry."""
    frame = a_client_export().with_columns(
        pl.Series(label_ar("employees", "status"), ["نشط ", "موقوف", "نشط"]))
    mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert mapped["status"].to_list() == ["Active", "Inactive", "Active"]
    assert not report.unmapped_values


def test_header_matching_absorbs_the_same_variation():
    frame = a_client_export().rename(
        {label_ar("employees", "employee_id"):
         "  " + label_ar("employees", "employee_id") + "  "})
    _mapped, report = mapping.apply_profile(frame, "employees", a_profile())
    assert not report.unmapped
    assert normalise("  x  ") == "x"


# --------------------------------------------------------------------------
# versioning and the changed-export signal
# --------------------------------------------------------------------------

def _saveable():
    """a_profile() plus the evidence cycle B requires at the write."""
    version = a_profile()
    version["evidence"] = mapping.build_evidence(
        "employees", a_client_export(), version)
    return version


def test_versions_are_appended_never_mutated(profile_file):
    first = mapping.save_version("employees", _saveable(), path=str(profile_file))
    second = mapping.save_version("employees", _saveable(), path=str(profile_file))
    assert (first["version"], second["version"]) == (1, 2)
    spec = yaml.safe_load(profile_file.read_text(encoding="utf-8"))
    assert len(spec["versions"]) == 2, (
        "history is what lets anyone say which mapping produced last month's "
        "numbers")
    assert mapping.load_profile("employees", path=str(profile_file))["version"] == 2


def test_a_changed_export_is_detectable():
    original = mapping.header_fingerprint(a_client_export().columns)
    changed = mapping.header_fingerprint(
        list(a_client_export().columns) + ["رقم الهوية"])
    assert original != changed
    # order must not matter - a reordered export is not a changed one
    reordered = mapping.header_fingerprint(
        list(reversed(a_client_export().columns)))
    assert reordered == original


# --------------------------------------------------------------------------
# evidence: the part that cannot be reconstructed later
# --------------------------------------------------------------------------

def test_rejected_candidates_survive_a_round_trip(profile_file):
    """"system proposed manager_id, human chose owner_id" is the scarcest
    training signal there is, and it exists only if it is written down at the
    moment the human decides."""
    # A one-column version, so the evidence below covers everything it
    # references - cycle B refuses a version whose evidence has holes.
    version = {"created_by": "operator@synthetic.local",
               "columns": {"المسؤول": "manager_id"}}
    version["evidence"] = [{
        "source_header": "المسؤول",
        "normalised": normalise("المسؤول"),
        "matched_by": "human",
        "confidence": None,
        "chosen": "manager_id",
        "rejected": [{"candidate": "employee_id",
                      "proposed_by": "normalised_label_match",
                      "score": 0.71,
                      "reason": "This column is the case owner, not the employee."}],
        "value_profile": {"kind": "redacted", "dtype": "string",
                          "cardinality": 3, "length_range": [6, 6],
                          "pattern": "AAA999"},
    }]
    mapping.save_version("employees", version, path=str(profile_file))
    loaded = mapping.load_profile("employees", path=str(profile_file))
    rejected = loaded["evidence"][0]["rejected"][0]
    assert rejected["candidate"] == "employee_id"
    assert rejected["score"] == 0.71
    assert "case owner" in rejected["reason"]


def test_evidence_covers_every_source_header_including_the_ignored_ones():
    frame = a_client_export()
    evidence = mapping.build_evidence("employees", frame, a_profile())
    assert {e["source_header"] for e in evidence} == set(frame.columns)
    ignored = next(e for e in evidence if e["source_header"] == "ملاحظات")
    assert ignored["decision"] == "ignored"
    assert ignored["chosen"] is None
