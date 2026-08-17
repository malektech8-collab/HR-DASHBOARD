# -*- coding: utf-8 -*-
"""A withheld count is NULL, and NULL must not crash, lie, or disagree.

THREE FINDINGS FROM THE FIRST REAL LOAD, all of the same shape: a client did
not supply a column, and three different surfaces disagreed about what that
means.

  P0  /api/workforce/summary returned HTTP 500. The mart withholds
      missing_cost_center_count as NULL when the export has no cost-centre
      column; the endpoint compared it to 0. The whole Workforce page was
      down for the first real client.

  P1  manager_id was never gated the way cost_center was, so with no manager
      column the check fired once per active employee - 85% of every row on
      the client's Data Quality page - burying several hundred Critical
      missing-salary findings.

  P1  The same fact answered two ways: NULL in mart_workforce_kpis, 0 in
      mart_data_quality_summary. Two independent mechanisms, only one fired.

WHY DEMO COULD NOT CATCH ANY OF THEM. The sample data supplies every column
these counters read, so every count is a real integer, every comparison has
two numbers, and every gate is TRUE. The suite was green throughout. Only a
client who does not supply a column reaches the NULL.

Per SP-001 each assertion is paired with a tamper.
"""
import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from app.api import _provenance as p          # noqa: E402
from app.api.workforce import _count_card     # noqa: E402

_MODELS = os.path.join(_ROOT, "dbt_analytics", "models", "marts")

REGISTRY = {
    "domains": {
        "contracted": {"employees": ["employees"], "locations": ["locations"]},
        "uncontracted": {},
    },
    "marts": {
        "mart_workforce_kpis": {
            "mode": "column",
            "columns": {
                "missing_manager_count": ["employees"],
                "missing_cost_center_count": ["employees"],
                "missing_project_count": ["employees", "locations"],
            },
        },
    },
}
MART = "mart_workforce_kpis"


def prov(*provided):
    return p.Provenance(provided=set(provided), registry=REGISTRY,
                        data_mode="real", coverage={})


def _sql(name):
    with open(os.path.join(_MODELS, name), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# P0 - a NULL count must not take the page down
# --------------------------------------------------------------------------

def test_a_withheld_count_does_not_raise():
    """The exact crash: TypeError: '>' not supported between NoneType and int."""
    card = _count_card(prov("employees"), MART,
                       {"missing_cost_center_count": None},
                       "missing_cost_center_count", "Missing Cost Center")
    assert card.value is None


def test_a_withheld_count_is_NEUTRAL_never_healthy():
    """`healthy` asserts that nothing is missing - which is precisely the
    claim the NULL exists to avoid making."""
    card = _count_card(prov("employees"), MART,
                       {"missing_cost_center_count": None},
                       "missing_cost_center_count", "Missing Cost Center")
    assert card.status == "neutral"


def test_a_real_count_still_colours_itself():
    """The tamper. A guard that neutralised everything would pass the test
    above while making the card useless for a client who DOES supply it."""
    warned = _count_card(prov("employees"), MART,
                         {"missing_cost_center_count": 7},
                         "missing_cost_center_count", "Missing Cost Center")
    clean = _count_card(prov("employees"), MART,
                        {"missing_cost_center_count": 0},
                        "missing_cost_center_count", "Missing Cost Center")
    assert (warned.value, warned.status) == (7, "warning")
    assert (clean.value, clean.status) == (0, "healthy")


def test_zero_is_healthy_only_when_it_was_actually_MEASURED():
    """0 and NULL are different answers and must never render alike: one says
    nobody is missing a cost centre, the other says we cannot know."""
    measured = _count_card(prov("employees"), MART,
                           {"missing_cost_center_count": 0},
                           "missing_cost_center_count", "Missing Cost Center")
    withheld = _count_card(prov("employees"), MART,
                           {"missing_cost_center_count": None},
                           "missing_cost_center_count", "Missing Cost Center")
    assert measured.status != withheld.status
    assert measured.value != withheld.value


def test_a_domain_suppressed_count_is_also_withheld_not_zero():
    """The other reason a value can be absent. prov.value() nulls the column
    when its DOMAIN is missing; the guard must handle that path too."""
    card = _count_card(prov("employees"), MART,          # locations absent
                       {"missing_project_count": 2170},
                       "missing_project_count", "Missing Project")
    assert card.value is None and card.status == "neutral"


# --------------------------------------------------------------------------
# P1 - manager_id gated exactly as cost_center is
# --------------------------------------------------------------------------

@pytest.mark.parametrize("model,var", [
    ("mart_workforce_kpis.sql", "has_manager_id_source_sql"),
    ("mart_workforce_exceptions.sql", "has_manager_id_source_sql"),
    ("mart_data_quality_summary.sql", "has_manager_id_source_sql"),
    ("mart_workforce_exceptions.sql", "has_locations_source_sql"),
])
def test_the_gate_is_present_in_the_model(model, var):
    assert var in _sql(model)


def test_the_manager_gate_reaches_every_surface_cost_center_reaches():
    """The rule, not a list. cost_center was gated on four surfaces and
    manager_id on none; anything reading one and not the other is the next
    instance of this defect."""
    for name in os.listdir(_MODELS):
        sql = _sql(name)
        if "has_cost_center_source_sql" not in sql:
            continue
        # mart_recruitment_exceptions reads the REQUISITION's cost centre,
        # from the recruitment domain - a different column of a different
        # file, which this employees-file var must not gate.
        if "manager_id" not in sql:
            continue
        assert "has_manager_id_source_sql" in sql, name


def test_validate_data_gates_the_manager_check():
    with open(os.path.join(_ROOT, "scripts", "validate_data.py"),
              encoding="utf-8") as handle:
        source = handle.read()
    assert 'provides_column("employees", "manager_id")' in source
    # And the tamper: the else-branch must SAY the check was skipped, or the
    # silence is indistinguishable from a clean file.
    assert "no manager_id column" in source


def test_the_gates_are_wired_from_the_onboarding_registry():
    """A var defaulted in dbt_project.yml but never overridden at runtime is
    a window this repository chose for every client - the class test_dbt_vars
    exists for. These must be resolved per client."""
    with open(os.path.join(_ROOT, "scripts", "build_warehouse.py"),
              encoding="utf-8") as handle:
        source = handle.read()
    for var in ("has_manager_id_source_sql", "has_locations_source_sql"):
        assert var in source, var
    assert 'provides_column("employees", "manager_id")' in source


# --------------------------------------------------------------------------
# P1 - the two marts must answer the same fact the same way
# --------------------------------------------------------------------------

@pytest.mark.parametrize("column,var", [
    ("missing_manager_count", "has_manager_id_source_sql"),
    ("missing_cost_center_count", "has_cost_center_source_sql"),
    ("missing_project_count", "has_locations_source_sql"),
])
def test_both_marts_withhold_the_same_counter(column, var):
    for model in ("mart_workforce_kpis.sql", "mart_data_quality_summary.sql"):
        sql = _sql(model)
        assert column in sql, model
        assert var in sql, model


def test_neither_mart_counts_the_column_unconditionally():
    """The tamper that matters: it is not enough for the var to APPEAR in the
    file. An unguarded COUNT beside a guarded one still answers 0."""
    for model in ("mart_workforce_kpis.sql", "mart_data_quality_summary.sql"):
        sql = _sql(model)
        for line in sql.splitlines():
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if re.search(r"missing_(manager|cost_center|project)_count",
                         stripped) and stripped.upper().startswith("COUNT("):
                pytest.fail("{}: unguarded COUNT -> {}".format(model, stripped))


def test_the_provenance_registry_knows_project_needs_locations():
    """`project` is resolved through the client's locations FILE. Declaring it
    as employees-only made a missing REFERENCE FILE render as thousands of
    broken employee records."""
    import yaml
    with open(os.path.join(_ROOT, "config", "metric_provenance.yml"),
              encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)
    for mart in ("mart_workforce_kpis", "mart_data_quality_summary"):
        entry = registry["marts"][mart]["columns"]["missing_project_count"]
        domains = entry["domains"] if isinstance(entry, dict) else entry
        assert "locations" in domains, mart
        assert "employees" in domains, mart


def test_every_contracted_domain_has_a_bilingual_label():
    """`locations` became reachable as a suppression reason only when
    missing_project_count was corrected to depend on it, and it had no label -
    so the first client to see it would have read "Not yet provided:
    locations.", lowercase in English and untranslated in Arabic.

    Asserted for the whole set rather than that one name: the next domain to
    become reachable should fail here, not on a client's screen.
    """
    import yaml
    with open(os.path.join(_ROOT, "config", "metric_provenance.yml"),
              encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)
    contracted = set(registry["domains"]["contracted"])
    assert contracted, "registry lists no contracted domains"
    for domain in sorted(contracted):
        assert domain in p.DOMAIN_LABELS_EN, domain
        assert domain in p.DOMAIN_LABELS_AR, domain
        # And the tamper: a label that is just the key is not a label.
        assert p.DOMAIN_LABELS_EN[domain] != domain, domain
        assert p.DOMAIN_LABELS_AR[domain] != domain, domain
