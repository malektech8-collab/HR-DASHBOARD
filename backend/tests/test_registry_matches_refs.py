# -*- coding: utf-8 -*-
"""A mart may not DECLARE a domain it cannot REACH.

THE SPECIES THIS CATCHES is the mirror of everything else in this suite. Every
other guard here asks *was a figure served when it should have been withheld* -
fabrication. This one asks the opposite: **was a figure WITHHELD when it could
have been served**.

That inversion is dangerous because the whole review posture is tuned to catch
fabrication. A wrongly-withheld figure looks exactly like the correct behaviour
thirty cycles were spent building: it is honest-looking, it cites a reason, and
the reason is false. Nothing on the page is wrong. The client simply does not
get a number they are entitled to, and is told a file is missing that the
figure never needed.

It is invisible to demo, because demo provides every domain and nothing ever
suppresses. It is invisible to review, because "withheld: not yet provided" is
the shape we want to see. It is visible only by comparing what a model ACTUALLY
READS against what the registry CLAIMS - which is what this does.

HOW. Build the ref graph from `ref()` and `source()`, resolve each mart's
reachable domains through the registry's own domain->table mapping, and flag
any DECLARED domain that is not reachable.

WHAT IT DELIBERATELY DOES NOT DO:

  * It does not flag UNDER-declaration - a mart that reaches a domain without
    declaring it. Reaching is not using: a model may ref a base model that
    touches six domains and read a column from one. That direction needs
    column-level analysis and would be mostly false positives.

  * It ABSTAINS rather than guesses when a model's upstream is not fully
    resolvable in dbt's graph - anything reading a warehouse table
    build_warehouse loads from parquet, and anything downstream of
    `data_quality`, which validate_data assembles from every domain at once. A
    check that guessed there would flag real dependencies it simply cannot see.

  * Comments are stripped before parsing. Prose has tripped three structural
    rules in this repository now; a rule about SQL must read SQL.
"""
import io
import os
import re
import sys

import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

_MODELS_DIR = os.path.join(_ROOT, "dbt_analytics", "models")
_REGISTRY = os.path.join(_ROOT, "config", "metric_provenance.yml")

_REF = re.compile(r"ref\(\s*'([^']+)'\s*\)")
_SOURCE = re.compile(r"source\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")
_CTE = re.compile(r"(?:WITH|,)\s*([a-z_][a-z0-9_]*)\s+AS\s*\(", re.I)
_BARE = re.compile(r"\b(?:FROM|JOIN)\s+(?!\{\{)([a-z_][a-z0-9_]*)\b", re.I)
_SQL_KEYWORDS = {"select", "lateral", "unnest", "values", "range"}

# Sources whose CONTENT comes from outside dbt's graph. `data_quality` is a
# gold parquet validate_data assembles from every domain, so a dependency on it
# is a dependency on all of them - unreachable by ref analysis, and not a
# defect. Abstain rather than flag.
_OPAQUE_SOURCES = {"data_quality"}

# Entries where the declared domain is TOPICAL rather than a data dependency:
# the payload is ABOUT those modules without reading their tables. Listed
# explicitly, with a reason, so each is a decision someone made rather than a
# silent exemption - and so removing one is a visible act.
_TOPICAL = {
    ("base_command_center_module_registry", "(payload)"):
        "a static list of MODULES; it names the domains it describes and reads none",
    ("mart_command_center_navigation_status", "(payload)"):
        "navigation over the same module list; same reason",
    ("mart_command_center_filter_options", "(payload)"):
        "filter options offered for modules it does not itself read",
}


def _strip_comments(sql):
    out = []
    for line in sql.splitlines():
        index = line.find("--")
        out.append(line if index == -1 else line[:index])
    return "\n".join(out)


def _models():
    found = {}
    for base, _dirs, names in os.walk(_MODELS_DIR):
        for name in names:
            if name.endswith(".sql"):
                with io.open(os.path.join(base, name), encoding="utf-8") as handle:
                    found[name[:-4]] = _strip_comments(handle.read())
    return found


def _registry():
    with io.open(_REGISTRY, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _table_to_domain(registry):
    mapping = {}
    for group in ("contracted", "uncontracted"):
        for domain, tables in (registry["domains"].get(group) or {}).items():
            for table in tables:
                mapping[table] = domain
    return mapping


def _opaque_tables(sql):
    """Bare table names that are neither a CTE nor a dbt ref/source."""
    ctes = {c.lower() for c in _CTE.findall(sql)}
    return {b.lower() for b in _BARE.findall(sql)} - ctes - _SQL_KEYWORDS


def _reachable(model, models, table_to_domain, seen=None):
    """(domains, resolvable). `resolvable` is False where we cannot see."""
    seen = seen or set()
    if model in seen:
        return set(), True
    seen.add(model)
    sql = models.get(model)
    if sql is None:
        return set(), False
    if _opaque_tables(sql):
        return set(), False
    sources = {table for _schema, table in _SOURCE.findall(sql)}
    if sources & _OPAQUE_SOURCES:
        return set(), False
    domains = {table_to_domain[t] for t in sources if t in table_to_domain}
    resolvable = True
    for ref in _REF.findall(sql):
        found, ok = _reachable(ref, models, table_to_domain, seen)
        domains |= found
        resolvable = resolvable and ok
    return domains, resolvable


def _declared_entries(spec):
    if spec.get("mode") == "column":
        return [(column, set((entry["domains"] if isinstance(entry, dict)
                              else entry) or []))
                for column, entry in (spec.get("columns") or {}).items()]
    return [("(payload)", set(spec.get("domains") or []))]


def _findings():
    models, registry = _models(), _registry()
    table_to_domain = _table_to_domain(registry)
    findings, abstained = [], []
    for mart, spec in registry["marts"].items():
        if mart not in models:
            abstained.append(mart)
            continue
        reachable, resolvable = _reachable(mart, models, table_to_domain)
        if not resolvable:
            abstained.append(mart)
            continue
        for column, declared in _declared_entries(spec):
            unreachable = declared - reachable
            if unreachable and (mart, column) not in _TOPICAL:
                findings.append((mart, column, sorted(unreachable)))
    return findings, abstained


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------

def test_no_mart_declares_a_domain_it_cannot_reach():
    findings, _abstained = _findings()
    assert not findings, (
        "these marts withhold on a domain they never read - a figure denied "
        "for a reason that is false:\n  "
        + "\n  ".join("{}: {} declares {}".format(m, c, d)
                      for m, c, d in sorted(findings)))


def test_the_check_actually_sees_most_of_the_registry():
    """The emptiness guard. Abstention is honest, but a check that abstained on
    everything would pass while inspecting nothing."""
    _findings_, abstained = _findings()
    registry = _registry()
    checked = len(registry["marts"]) - len(abstained)
    assert checked >= 50, (
        "only {} of {} marts were checked; the graph parser has probably "
        "stopped resolving refs".format(checked, len(registry["marts"])))


# --------------------------------------------------------------------------
# the tampers - SP-001
# --------------------------------------------------------------------------

def test_it_catches_a_declared_but_unreachable_domain():
    """The exact shape of the step-2 leftovers, on a synthetic registry."""
    models = {"m": "SELECT 1 FROM {{ ref('s') }}",
              "s": "SELECT 1 FROM {{ source('hr_raw', 'employees') }}"}
    reachable, resolvable = _reachable("m", models, {"employees": "employees"})
    assert resolvable and reachable == {"employees"}
    assert {"compliance"} - reachable == {"compliance"}


def test_it_accepts_a_domain_that_IS_reached():
    """The other half, or the rule above is just a ban on declaring anything."""
    models = {"m": "SELECT 1 FROM {{ ref('s') }}",
              "s": "SELECT 1 FROM {{ source('hr_raw', 'compliance') }}"}
    reachable, resolvable = _reachable("m", models, {"compliance": "compliance"})
    assert resolvable and not ({"compliance"} - reachable)


def test_it_abstains_on_a_table_dbt_does_not_build():
    models = {"m": "SELECT 1 FROM command_center_module_checks"}
    _domains, resolvable = _reachable("m", models, {})
    assert not resolvable


def test_it_abstains_downstream_of_data_quality():
    """validate_data assembles that table from every domain at once, so a
    dependency on it is a dependency on all of them."""
    models = {"m": "SELECT 1 FROM {{ ref('s') }}",
              "s": "SELECT 1 FROM {{ source('hr_raw', 'data_quality') }}"}
    _domains, resolvable = _reachable("m", models, {})
    assert not resolvable


def test_comments_do_not_create_dependencies():
    """Prose has tripped three structural rules in this repository. A `FROM`
    inside a sentence is not a table."""
    sql = _strip_comments("-- read from the compliance file\nSELECT 1 FROM x")
    assert _opaque_tables(sql) == {"x"}


# --------------------------------------------------------------------------
# the two leftovers this cycle fixed, pinned
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mart", [
    "mart_workforce_iqama_expiry",
    "mart_workforce_exceptions",
])
def test_the_step_2_leftovers_no_longer_declare_compliance(mart):
    registry = _registry()
    assert "compliance" not in set(registry["marts"][mart]["domains"])


def test_iqama_expiring_30_no_longer_declares_compliance():
    registry = _registry()
    entry = registry["marts"]["mart_workforce_kpis"]["columns"]["iqama_expiring_30"]
    domains = entry["domains"] if isinstance(entry, dict) else entry
    assert "compliance" not in set(domains)


def test_the_dead_compliance_join_is_gone():
    with io.open(os.path.join(_MODELS_DIR, "marts", "mart_workforce_kpis.sql"),
                 encoding="utf-8") as handle:
        sql = _strip_comments(handle.read())
    assert "stg_compliance" not in sql


def test_every_topical_exemption_states_a_reason():
    """An exemption without a reason is an exemption nobody can re-examine."""
    for key, reason in _TOPICAL.items():
        assert isinstance(reason, str) and len(reason) > 30, key
