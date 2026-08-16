# -*- coding: utf-8 -*-
"""Optional canonical columns, and constants asserted by an operator.

WHAT THIS CYCLE FIXED. The first real client export could not load: three
canonical columns were `required: true` and had no source header. They are
contract defects rather than client gaps - `company` assumed a multi-entity
client, `job_family` is a derived taxonomy, `cost_center` lives in finance.

`required: false` alone would have been worse than the rejection it removed.
`required: true` guaranteed both that a column was PRESENT and that it EXISTED
downstream; relaxing removes only the first, and the second failed as a CRASH.
Both measured, and both are pinned below.
"""
import os
import sys

import polars as pl
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import canonical_schema as cs  # noqa: E402
import mapping  # noqa: E402
import onboarding as onb  # noqa: E402

THREE = ("company", "job_family", "cost_center")


def _employees(omit=()):
    frame = {}
    for spec in cs.columns("employees"):
        name = spec["name"]
        if name in omit or name == "is_saudi":
            continue
        if name == "employee_id":
            frame[name] = ["E1", "E2"]
        elif name == "status":
            frame[name] = ["Active", "Active"]
        elif name == "joining_date":
            frame[name] = ["2024-01-15", "2023-06-01"]
        elif name in ("termination_date", "end_of_service_type"):
            frame[name] = ["", ""]
        elif name == "contract_end_date":
            frame[name] = ["2027-01-01"] * 2
        elif spec.get("allowed_values"):
            frame[name] = [spec["allowed_values"][0]] * 2
        elif str(spec.get("type", "")).upper() == "DECIMAL":
            frame[name] = ["5000", "5000"]
        else:
            frame[name] = ["X1", "X2"]
    return pl.DataFrame(frame)


# --------------------------------------------------------------------------
# (a) the three are optional, and their absence no longer crashes
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column", THREE)
def test_the_three_are_optional(column):
    assert column not in cs.required_columns("employees")


def test_a_file_missing_all_three_is_ACCEPTED(tmp_path):
    import validate_schema as vs

    path = tmp_path / "employees.csv"
    _employees(omit=THREE).write_csv(str(path))
    result = vs.validate_csv(str(path), "employees")
    assert result.rejects == [], [v.rule for v in result.rejects]


def test_shape_completion_adds_them_as_TYPED_NULLS():
    frame = _employees(omit=THREE)
    completed, absent = onb.complete_canonical_shape(frame, "employees")
    assert absent == sorted(THREE)
    for column in THREE:
        assert column in completed.columns
        assert completed[column].null_count() == completed.height
        assert completed.schema[column] == pl.Utf8


def test_the_crash_this_prevents_is_real():
    """SP-001: the failure mode, demonstrated, not asserted.

    Without completion, validate_data's own idiom raises rather than returning
    an empty selection - so the file would be accepted at the gate and then
    crash mid-pipeline.
    """
    frame = _employees(omit=THREE)
    with pytest.raises(Exception) as excinfo:
        frame.filter(pl.col("cost_center").is_null())
    assert "cost_center" in str(excinfo.value)

    completed, _ = onb.complete_canonical_shape(frame, "employees")
    assert completed.filter(pl.col("cost_center").is_null()).height == 2


def test_a_REQUIRED_column_is_NEVER_completed():
    """Filling a required column silently would be the fabrication this whole
    phase removes. Its absence stays a REJECT at the gate."""
    frame = _employees(omit=("department",))
    completed, absent = onb.complete_canonical_shape(frame, "employees")
    assert "department" not in absent
    assert "department" not in completed.columns


def test_a_DERIVED_column_is_NEVER_completed():
    """is_saudi is produced from nationality, and ingest derives it only when
    the column is ABSENT. Completing it first would make the derivation skip
    itself and compute every Saudization figure from nulls - silent, and
    favourable-looking. The first run of this cycle's proof did exactly that.
    """
    frame = _employees(omit=THREE)
    _completed, absent = onb.complete_canonical_shape(frame, "employees")
    assert "is_saudi" not in absent


# --------------------------------------------------------------------------
# (b) an absent column is a coverage fact, not one exception per employee
# --------------------------------------------------------------------------

def test_provision_is_recorded_and_readable(tmp_path):
    registry = str(tmp_path / "declared_domains.yml")
    onb.record_provided_columns("employees", ["cost_center"], path=registry)
    assert onb.absent_columns("employees", path=registry) == ["cost_center"]
    assert onb.provides_column("employees", "cost_center", path=registry) is False
    assert onb.provides_column("employees", "department", path=registry) is True


def test_provision_defaults_to_TRUE_with_no_registry(tmp_path):
    """Every deployment that has not been through an upload must behave exactly
    as before - the cost-centre checks keep firing."""
    missing = str(tmp_path / "absent.yml")
    assert onb.provides_column("employees", "cost_center", path=missing) is True


def test_nullness_can_no_longer_answer_the_question():
    """WHY provision is recorded separately rather than inferred.

    After completion the column exists and is NULL whether the client omitted
    it or supplied it blank. Those are a coverage fact and a data-quality
    exception, and the data can no longer tell them apart.
    """
    omitted, _ = onb.complete_canonical_shape(
        _employees(omit=("cost_center",)), "employees")
    supplied_blank = _employees()
    supplied_blank = supplied_blank.with_columns(
        pl.lit(None, dtype=pl.Utf8).alias("cost_center"))
    assert omitted["cost_center"].null_count() == \
        supplied_blank["cost_center"].null_count()


@pytest.mark.parametrize("model,marker", [
    ("mart_workforce_exceptions.sql", "has_cost_center_source_sql"),
    ("mart_compliance_exceptions.sql", "has_cost_center_source_sql"),
    ("mart_payroll_exceptions.sql", "has_cost_center_source_sql"),
    ("mart_workforce_kpis.sql", "has_cost_center_source_sql"),
])
def test_the_four_surfaces_are_gated(model, marker):
    path = os.path.join(_ROOT, "dbt_analytics", "models", "marts", model)
    with open(path, encoding="utf-8") as handle:
        assert marker in handle.read(), model


def test_the_sentinel_is_gone_from_both_payroll_bases():
    """A sentinel renders an absence as a value. A client with no cost centres
    would get a payroll breakdown bucketed under a category literally named
    'Missing Cost Center' - COALESCE(project,'Unassigned') in a second place."""
    for model in ("base_payroll_current.sql", "base_payroll_previous.sql"):
        path = os.path.join(_ROOT, "dbt_analytics", "models", "marts", model)
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
        assert "COALESCE(e.cost_center" not in body, model


def test_the_var_defaults_TRUE_so_existing_deployments_are_unchanged():
    path = os.path.join(_ROOT, "dbt_analytics", "dbt_project.yml")
    with open(path, encoding="utf-8") as handle:
        body = handle.read()
    assert 'has_cost_center_source_sql: "TRUE"' in body


# --------------------------------------------------------------------------
# (c) a constant is signed and based
# --------------------------------------------------------------------------

@pytest.fixture
def profile(tmp_path, monkeypatch):
    monkeypatch.setattr(mapping, "PROFILE_DIR", str(tmp_path))
    monkeypatch.setattr(mapping, "CONTAINER_PROFILE_DIR", str(tmp_path))
    return str(tmp_path / "employees.yml")


def _version(constants, confirmations=None):
    version = {
        "created_by": "operator@client.example",
        "columns": {"Emp No": "employee_id"},
        "constants": constants,
        "evidence": [{"source_header": "Emp No", "chosen": "employee_id",
                      "decision": "mapped", "matched_by": "human",
                      "confidence": None, "rejected": [],
                      "value_profile": {"kind": "redacted", "dtype": "string",
                                        "cardinality": 2,
                                        "length_range": [2, 2],
                                        "pattern": "A9"}}],
    }
    if confirmations:
        version["confirmations"] = confirmations
    return version


SIGNED = {"value": "Acme", "asserted_by": "op@x",
          "basis": "Single legal entity, confirmed with the HR manager."}


def test_a_signed_and_based_constant_saves(profile):
    saved = mapping.save_version("employees", _version({"company": SIGNED}),
                                 path=profile)
    assert saved["constants"]["company"]["value"] == "Acme"


@pytest.mark.parametrize("constant,missing", [
    ({"value": "Acme"}, "asserted_by"),
    ({"value": "Acme", "asserted_by": "op@x"}, "basis"),
    ({"value": "Acme", "basis": "Single entity."}, "asserted_by"),
    ({"value": "Acme", "asserted_by": " ", "basis": " "}, "asserted_by"),
])
def test_an_unsigned_or_unbased_constant_is_REFUSED(profile, constant, missing):
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version("employees", _version({"company": constant}),
                             path=profile)
    assert missing in str(excinfo.value)


def test_a_bare_value_is_REFUSED(profile):
    with pytest.raises(mapping.MappingError):
        mapping.save_version("employees", _version({"company": "Acme"}),
                             path=profile)


def test_a_constant_may_not_target_a_REQUIRED_column(profile):
    """Otherwise it becomes a way past the required-columns gate - which is
    exactly what relaxing the three was meant to make unnecessary."""
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version(
            "employees",
            _version({"department": dict(SIGNED, value="Ops")}), path=profile)
    assert "REQUIRED" in str(excinfo.value)


def test_a_constant_may_not_overwrite_a_mapped_column():
    """A constant is for a column the client does NOT have, not a way to
    override one they do."""
    frame = pl.DataFrame({"Emp No": ["E1"], "Co": ["Real Co"]})
    version = {"columns": {"Emp No": "employee_id", "Co": "company"},
               "constants": {"company": SIGNED}}
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.apply_profile(frame, "employees", version)
    assert "already mapped" in str(excinfo.value)


def test_applying_a_constant_sets_every_row_and_preserves_them():
    frame = pl.DataFrame({"Emp No": ["E1", "E2", "E3"]})
    version = {"columns": {"Emp No": "employee_id"},
               "constants": {"company": SIGNED}}
    mapped, report = mapping.apply_profile(frame, "employees", version)
    assert mapped["company"].to_list() == ["Acme"] * 3
    assert mapped.height == 3
    assert report.constants == {"company": "Acme"}


def test_the_report_separates_asserted_from_client_supplied():
    """A reader must be able to tell which values came from the client."""
    frame = pl.DataFrame({"Emp No": ["E1"]})
    version = {"columns": {"Emp No": "employee_id"},
               "constants": {"company": SIGNED}}
    _mapped, report = mapping.apply_profile(frame, "employees", version)
    assert "company" in report.as_dict()["constants"]
    assert "company" not in report.as_dict()["renamed"]


# --------------------------------------------------------------------------
# (d) the affirmation rule - visibility, not column type
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column,needs", [
    ("company", False),              # free text; wrong is loud
    ("cost_center", False),
    ("job_family", False),
    ("status", True),                # gated enum; wrong is silent
    ("end_of_service_type", True),
    ("employment_type", True),
    ("contract_type", True),
    ("location", True),              # free text, and the case that proves
])                                   # the rule is about VISIBILITY
def test_the_affirmation_rule(column, needs):
    assert mapping.constant_needs_affirmation("employees", column) is needs


def test_location_needs_one_despite_being_free_text():
    """The exception that proves the rule.

    `location` carries no allowed_values, so a type-based rule would let it
    through. It feeds the locations join, so a constant location for a
    multi-site client renders as a clean single-site chart - confident, wrong,
    and indistinguishable from a client who genuinely has one site.
    """
    assert not mapping._allowed_values("employees", "location"), (
        "location carries no vocabulary, so a type-based rule would let it "
        "through")
    assert mapping.constant_needs_affirmation("employees", "location") is True


def test_a_location_constant_is_refused_TODAY_for_a_different_reason():
    """An honest limitation, pinned so it is not mistaken for the rule
    working.

    `location` is still REQUIRED, so the required-column guard refuses a
    location constant before the affirmation check is ever reached. The
    affirmation rule for it is implemented and tested above, and becomes
    REACHABLE only if location is ever relaxed. Two guards agreeing is not
    the same as one guard working.
    """
    assert "location" in cs.required_columns("employees")


def test_an_unaffirmed_constant_on_a_gated_column_is_REFUSED(profile):
    """`end_of_service_type` is the only OPTIONAL gated column, so it is the
    only one that reaches the affirmation check rather than stopping at the
    required-column guard."""
    with pytest.raises(mapping.MappingError) as excinfo:
        mapping.save_version(
            "employees",
            _version({"end_of_service_type": dict(SIGNED, value="Resignation")}),
            path=profile)
    assert "affirmation" in str(excinfo.value)


def test_an_affirmed_constant_on_a_gated_column_saves(profile):
    saved = mapping.save_version(
        "employees",
        _version({"end_of_service_type": dict(SIGNED, value="Resignation")},
                 confirmations={"end_of_service_type": {
                     "confirmed_by": "op@x", "pairs": {},
                     "confirmed_at": "2026-08-13T09:00:00"}}),
        path=profile)
    assert saved["constants"]["end_of_service_type"]["value"] == "Resignation"


# --------------------------------------------------------------------------
# job_family - stated, not worked around
# --------------------------------------------------------------------------

def test_job_family_has_no_consumer():
    """Measured, and recorded so nobody manufactures work for it.

    Relaxing job_family changes nothing observable because nothing observes it.
    """
    roots = [os.path.join(_ROOT, "dbt_analytics", "models"),
             os.path.join(_ROOT, "backend", "app"),
             os.path.join(_ROOT, "frontend", "src")]
    hits = []
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            if "node_modules" in dirpath or "__pycache__" in dirpath:
                continue
            for name in files:
                if not name.endswith((".sql", ".py", ".ts", ".tsx")):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8", errors="ignore") as handle:
                    if "job_family" in handle.read():
                        hits.append(os.path.relpath(path, _ROOT))
    assert hits == [], (
        "job_family gained a consumer - the relaxation note in the contract "
        "says it has none, and one of them is now wrong: " + str(hits))


# --------------------------------------------------------------------------
# the constructor and the CLI can express a constant
# --------------------------------------------------------------------------

def test_build_version_carries_constants():
    """Without this a profile with a constant could only be hand-written -
    the state cycle A was in before the CLI existed."""
    frame = pl.DataFrame({"Emp No": ["E1", "E2"]})
    version = mapping.build_version(
        "employees", frame,
        {"Emp No": {"decision": "mapped", "chosen": "employee_id"}},
        created_by="op@x", constants={"company": SIGNED})
    assert version["constants"]["company"]["value"] == "Acme"
    assert version["constants"]["company"]["basis"]


def test_the_cli_stamps_asserted_by_but_never_the_basis():
    """`basis` is the operator's own words. A tool that wrote the
    justification would be recording nothing - the same reason the CLI
    supplies attribution for an affirmation but never the affirmation."""
    source = os.path.join(_ROOT, "scripts", "mapping_cli.py")
    with open(source, encoding="utf-8") as handle:
        body = handle.read()
    assert 'entry.setdefault("asserted_by", args.by)' in body
    assert 'setdefault("basis"' not in body
