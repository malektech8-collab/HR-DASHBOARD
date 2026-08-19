# -*- coding: utf-8 -*-
"""Every `has_*_source_sql` gate resolves from what the CLIENT provided.

SP-009's expiry condition in its general form. The register entry says a
default that preserves behaviour during a migration carries an expiry
condition, and that the condition belongs in a TEST rather than a comment,
because the day it stops holding is otherwise silent.

THE INSTANCE THIS GENERALISES. `has_gosi_source_sql` and `has_wps_source_sql`
resolved from `config/business_rules.yml`:

    compliance_rules:
      has_gosi_source_for_period: true
      has_wps_source_for_period: true

A repository literal deciding a client fact, defaulting True - so every
deployment claimed a GOSI and a WPS source whether or not the client had one,
and the two compliance arms these gate fired for clients with neither. It
escaped `test_dbt_vars` only because the values are booleans rather than
date-shaped, which is exactly the kind of near-miss that makes a rule worth
generalising rather than fixing case by case.

WHAT THIS TEST IS FOR. Not these two columns - they are fixed. It is for the
NEXT gate someone adds by copying a neighbour, and for the next config key that
looks like a reasonable place to put a client fact.
"""
import io
import os
import re
import sys

import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

_BUILD_WAREHOUSE = os.path.join(_ROOT, "scripts", "build_warehouse.py")
_PROJECT_YML = os.path.join(_ROOT, "dbt_analytics", "dbt_project.yml")
_RULES_YML = os.path.join(_ROOT, "config", "business_rules.yml")
_MODELS = os.path.join(_ROOT, "dbt_analytics", "models")

# A gate names a SOURCE the client either sent or did not.
_GATE = re.compile(r'"(has_\w*(?:source|sql))"\s*:', re.IGNORECASE)
# The two sanctioned ways to answer "did the client provide this?"
_FROM_PROVENANCE = ("provides_column", "load_declared")


def _source():
    return io.open(_BUILD_WAREHOUSE, encoding="utf-8").read()


def _gate_assignment(name, source):
    """The expression assigned to one gate var, up to the next var."""
    start = source.index('"{}":'.format(name))
    tail = source[start:]
    end = re.search(r'\n\s+"has_|\n\s+"critical_titles_sql"|\n\s*\}', tail)
    return tail[:end.start()] if end else tail


def _declared_gates():
    with io.open(_PROJECT_YML, encoding="utf-8") as handle:
        variables = yaml.safe_load(handle).get("vars") or {}
    return sorted(v for v in variables if v.startswith("has_"))


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------

def test_every_gate_resolves_from_provenance():
    """A gate answering from anywhere but the client's own file is a
    repository deciding a client fact."""
    source = _source()
    offenders = []
    for name in _declared_gates():
        if '"{}":'.format(name) not in source:
            offenders.append("{}: declared in dbt_project.yml but never "
                             "overridden at runtime".format(name))
            continue
        assignment = _gate_assignment(name, source)
        if not any(marker in assignment for marker in _FROM_PROVENANCE):
            offenders.append("{}: resolved from something other than "
                             "provenance".format(name))
    assert not offenders, (
        "every has_*_source gate must answer from what the CLIENT provided:\n  "
        + "\n  ".join(offenders))


def test_no_gate_is_answered_by_the_business_rules_config():
    """The specific shape that was there: a client fact in a repo config file,
    defaulting to the convenient answer."""
    with io.open(_RULES_YML, encoding="utf-8") as handle:
        rules = yaml.safe_load(handle) or {}
    offenders = []
    for section, body in (rules or {}).items():
        if not isinstance(body, dict):
            continue
        for key in body:
            if key.startswith("has_"):
                offenders.append("{}.{}".format(section, key))
    assert not offenders, (
        "these config keys answer a question only the client's file can "
        "answer: {}".format(offenders))


def test_the_deleted_keys_are_gone_not_merely_unread():
    """Superseding a config key leaves it able to win again after a refactor.
    Both were deleted."""
    text = io.open(_RULES_YML, encoding="utf-8").read()
    assert "has_gosi_source_for_period:" not in text
    assert "has_wps_source_for_period:" not in text
    # and the reason is recorded where the next reader will look for them.
    # Matched on a fragment that fits one line: the sentence itself wraps
    # across comment lines, so a longer literal would never match.
    assert "were DELETED in the" in text
    assert "repository literals deciding a" in text


# --------------------------------------------------------------------------
# the tampers - SP-001
# --------------------------------------------------------------------------

def test_the_rule_would_catch_a_config_resolved_gate():
    """A rule that matched nothing passes forever. This is the exact text that
    was in build_warehouse before this cycle."""
    fake = ('    "has_gosi_source_sql": "TRUE" if rules.get("compliance_rules", '
            '{}).get("has_gosi_source_for_period", True) else "FALSE",\n'
            '    "has_next_source_sql": (\n')
    assignment = _gate_assignment("has_gosi_source_sql", fake)
    assert not any(marker in assignment for marker in _FROM_PROVENANCE)


def test_the_rule_accepts_a_provenance_resolved_gate():
    """The other half: a correct gate must pass, or the test above is just a
    ban on the word."""
    fake = ('    "has_x_source_sql": (\n'
            '        "TRUE" if _onb.provides_column("employees", "x")\n'
            '        else "FALSE"),\n'
            '    "has_next_source_sql": (\n')
    assignment = _gate_assignment("has_x_source_sql", fake)
    assert any(marker in assignment for marker in _FROM_PROVENANCE)


def test_there_are_gates_to_check():
    """The emptiness guard. If the discovery ever stops finding vars, every
    assertion above passes vacuously."""
    gates = _declared_gates()
    assert len(gates) >= 10, gates


# --------------------------------------------------------------------------
# the two that were wrong
# --------------------------------------------------------------------------

@pytest.mark.parametrize("gate,column", [
    ("has_gosi_source_sql", "gosi_status"),
    ("has_wps_source_sql", "mudad_status"),
])
def test_the_compliance_gates_read_their_own_column(gate, column):
    assignment = _gate_assignment(gate, _source())
    assert 'provides_column("compliance", "{}")'.format(column) in \
        assignment.replace("\n", " ").replace("  ", " ") or \
        column in assignment, (gate, column)
