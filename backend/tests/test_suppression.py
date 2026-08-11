"""Phase 2 P0-3 step 2b: the suppression layer.

The rulings this file pins, each one the outcome of a finding rather than a
preference:

  * a suppressed payload is None, NEVER []          (step 2a ruling)
  * a suppressed KPI strip is None, never []        (found by 2b's own rig:
                                                     the first cut returned [])
  * default-deny: an unmapped mart is suppressed
  * every withheld figure is NAMED in the sibling block, bilingually
  * a suppressed mart is never QUERIED - the fabricated rows are not produced
  * column mode nulls columns; payload mode nulls the payload
  * scope_to_provided passes through (ruling 1's exception; step 4 filters it)

Synthetic only. No warehouse, no client data.
"""
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.api import _provenance as p  # noqa: E402

REGISTRY = {
    "domains": {
        "contracted": {"employees": ["employees"], "payroll": ["payroll"],
                       "attendance": ["attendance"]},
        "uncontracted": {"recruitment": ["candidates"], "talent": ["talent_reviews"]},
    },
    "marts": {
        "mart_kpis": {
            "mode": "column",
            "columns": {
                "report_month": [],
                "active_headcount": ["employees"],
                "payroll_cost": ["payroll"],
                "absence_days": ["attendance", "employees"],
                "data_quality_score": {
                    "domains": ["employees", "payroll"],
                    "scope_to_provided": True,
                },
            },
        },
        "mart_breakdown": {"mode": "payload", "domains": ["payroll"]},
        "mart_employees_only": {"mode": "payload", "domains": ["employees"]},
        "mart_metadata": {"mode": "payload", "domains": []},
        "mart_dq_exceptions": {
            "mode": "payload",
            "domains": ["employees", "payroll"],
            "scope_to_provided": True,
        },
    },
}


def prov(*provided):
    return p.Provenance(provided=set(provided), registry=REGISTRY, data_mode="real")


# --------------------------------------------------------------------------
# the core rule
# --------------------------------------------------------------------------

def test_a_payload_needs_every_domain_it_depends_on():
    assert prov("employees").payload("mart_employees_only") is True
    assert prov("employees").payload("mart_breakdown") is False


def test_multi_source_means_all_required():
    """A partially-sourced metric is not a real one."""
    assert prov("employees").column("mart_kpis", "absence_days") is False
    assert prov("employees", "attendance").column("mart_kpis", "absence_days") is True


def test_column_mode_nulls_columns_not_the_row():
    """The headcount is real; the payroll cost beside it is not."""
    provenance = prov("employees")
    assert provenance.value("mart_kpis", "active_headcount", 19) == 19
    assert provenance.value("mart_kpis", "payroll_cost", 446175.0) is None
    # the row itself is still served - suppressing it would take the real
    # figure down with the absent one
    assert provenance.payload("mart_kpis") is True


def test_a_domainless_column_passes_through():
    """A period label is not a measure."""
    assert prov().column("mart_kpis", "report_month") is True


# --------------------------------------------------------------------------
# null, never []
# --------------------------------------------------------------------------

def test_a_suppressed_payload_is_none_not_an_empty_list():
    provenance = prov("employees")
    result = provenance.rows("mart_breakdown", lambda: [{"a": 1}])
    assert result is None, "an empty list renders as an empty chart"


def test_a_fully_suppressed_kpi_strip_is_none_not_an_empty_list():
    """Found by this cycle's own real-mode rig: the first implementation
    returned [], which renders as 'this module has no KPIs'."""
    provenance = prov("employees")
    strip = provenance.kpis("mart_kpis", [
        ("payroll_cost", lambda: "card"),
    ])
    assert strip is None


def test_a_partly_suppressed_kpi_strip_keeps_the_real_cards():
    provenance = prov("employees")
    strip = provenance.kpis("mart_kpis", [
        ("active_headcount", lambda: "headcount"),
        ("payroll_cost", lambda: "cost"),
    ])
    assert strip == ["headcount"]


# --------------------------------------------------------------------------
# a suppressed mart is not merely filtered - it is not read
# --------------------------------------------------------------------------

def test_a_suppressed_mart_is_never_queried():
    """Producing the fabricated rows and discarding them leaves the fabricator
    one refactor away from emitting them."""
    calls = []

    def loader():
        calls.append(1)
        return [{"row": 1}]

    assert prov("employees").rows("mart_breakdown", loader) is None
    assert calls == [], "the query ran for a suppressed mart"


def test_kpi_factories_are_not_evaluated_when_suppressed():
    """The arithmetic that would build the card - round(rate * 100) - must not
    run against a NULL or fabricated figure."""
    def explode():
        raise AssertionError("a suppressed KPI factory was evaluated")

    assert prov("employees").kpis("mart_kpis", [("payroll_cost", explode)]) is None


# --------------------------------------------------------------------------
# default-deny
# --------------------------------------------------------------------------

def test_an_unmapped_mart_is_suppressed():
    provenance = prov("employees", "payroll", "attendance")
    assert provenance.payload("mart_that_nobody_mapped") is False
    entry = provenance.block()[0]
    assert entry.reason == p.NOT_MAPPED


def test_an_unmapped_column_is_suppressed():
    provenance = prov("employees")
    assert provenance.column("mart_kpis", "a_column_nobody_mapped") is False


# --------------------------------------------------------------------------
# the sibling block
# --------------------------------------------------------------------------

def test_every_withheld_figure_is_named_with_its_missing_domains():
    provenance = prov("employees")
    provenance.payload("mart_breakdown")
    provenance.column("mart_kpis", "absence_days")
    block = {item.key: item for item in provenance.block()}
    assert block["mart_breakdown"].missing_domains == ["payroll"]
    assert block["absence_days"].missing_domains == ["attendance"]


def test_the_message_is_bilingual_and_names_the_domain_in_words():
    provenance = prov("employees")
    provenance.payload("mart_breakdown")
    entry = provenance.block()[0]
    assert "Payroll" in entry.message_en
    assert "الرواتب" in entry.message_ar
    assert entry.reason == p.NOT_PROVIDED


def test_the_block_does_not_repeat_a_figure():
    provenance = prov("employees")
    for _ in range(3):
        provenance.payload("mart_breakdown")
    assert len(provenance.block()) == 1


def test_nothing_is_recorded_when_nothing_is_withheld():
    provenance = prov("employees", "payroll", "attendance")
    provenance.payload("mart_breakdown")
    provenance.column("mart_kpis", "payroll_cost")
    assert provenance.block() == []
    assert provenance.any_suppressed is False


# --------------------------------------------------------------------------
# the ruled exceptions
# --------------------------------------------------------------------------

def test_scope_to_provided_passes_through_rather_than_suppressing():
    """Ruling 1: these are FILTERED to the provided domains, not withheld.
    The filtering is step 4; 2b must not suppress them in the meantime."""
    provenance = prov("employees")
    assert provenance.column("mart_kpis", "data_quality_score") is True
    assert provenance.payload("mart_dq_exceptions") is True


def test_a_source_free_payload_passes_through():
    """Navigation and period metadata: suppressing them breaks the app rather
    than protecting a number."""
    assert prov().payload("mart_metadata") is True


# --------------------------------------------------------------------------
# module gating for the uncontracted domains
# --------------------------------------------------------------------------

def test_the_uncontracted_domains_gate_off_in_real_mode():
    """recruitment and talent have no contract, so they always load sample
    data. Serving them beside real figures is the fabrication being stopped."""
    import yaml

    with open(os.path.join(_ROOT, "config", "metric_provenance.yml"),
              encoding="utf-8") as handle:
        real = yaml.safe_load(handle)
    uncontracted = set(real["domains"]["uncontracted"])
    provenance = p.Provenance(
        provided=set(real["domains"]["contracted"]), registry=real, data_mode="real")
    gated = [name for name, spec in real["marts"].items()
             if spec.get("mode") == "payload"
             and set(spec.get("domains") or []) & uncontracted]
    assert gated, "expected recruitment/talent marts in the registry"
    for mart in gated:
        assert provenance.payload(mart) is False, mart
    print("\n[2b] uncontracted marts gated in real mode: {}".format(len(gated)))


def test_the_uncontracted_table_count_is_pinned():
    """16, not the 15 carried in the plan. Counted from the registry, which
    covers every silver table that has no contract."""
    import yaml

    with open(os.path.join(_ROOT, "config", "metric_provenance.yml"),
              encoding="utf-8") as handle:
        real = yaml.safe_load(handle)
    tables = {t for tables in real["domains"]["uncontracted"].values()
              for t in tables}
    assert len(tables) == 16, sorted(tables)


# --------------------------------------------------------------------------
# the substrate
# --------------------------------------------------------------------------

class _NoTable:
    def execute(self, *_a, **_kw):
        raise RuntimeError("no such table: domain_provenance")


def test_a_warehouse_without_the_provenance_table_denies_in_real_mode(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "DATA_MODE", "real", raising=False)
    assert p.provided_domains(_NoTable()) == set()


def test_a_warehouse_without_the_provenance_table_serves_demo(monkeypatch):
    """Demo means sample data; blacking out every page would be the wrong
    failure. Real mode is where default-deny has to hold."""
    from app.config import settings

    monkeypatch.setattr(settings, "DATA_MODE", "demo", raising=False)
    domains = p.provided_domains(_NoTable())
    assert "employees" in domains and "recruitment" in domains


def test_the_real_registry_loads_and_covers_every_mart_it_declares():
    registry = p.load_registry()
    assert registry.get("version") == 2
    marts = registry["marts"]
    for name, spec in marts.items():
        assert spec.get("mode") in ("column", "payload"), name
        if spec["mode"] == "column":
            assert spec.get("columns"), name
        else:
            assert "domains" in spec, name
    print("\n[2b] marts the suppression layer can decide on: {}".format(len(marts)))
