"""Tests for the declared-derivation mechanism (scripts/derivations.py).

Placed under backend/tests/ because that is the only path pytest collects
(pytest.ini testpaths). Adding a scripts/ test path is a later cleanup.

The behaviour under test is deliberately strict: is_saudi feeds the
Saudization percentage and Nitaqat banding, so an unrecognised nationality
must raise rather than quietly become False.
"""
import os
import sys

import pytest

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
)

from derivations import (  # noqa: E402
    DerivationError,
    REGISTRY,
    derive_column,
    nationality_is_saudi,
    resolve,
)


def test_recognises_saudi_variants():
    values = ["Saudi", "saudi", " SAUDI ", "Saudi Arabian", "KSA", "سعودي", "السعودية"]
    assert nationality_is_saudi(values) == [True] * len(values)


def test_recognises_non_saudi():
    assert nationality_is_saudi(["British", "Egyptian", "مصري"]) == [False, False, False]


def test_arabic_normalisation_handles_real_export_noise():
    # Alef/ya/ta-marbuta variants and stray spacing, as seen in real exports.
    assert nationality_is_saudi(["سعوديه", "سعودية", "  السعودية  "]) == [True, True, True]


def test_missing_nationality_is_unknown_not_false():
    # A blank nationality is a data-quality exception, not evidence of
    # non-Saudi status. Returning False here would understate Saudization.
    assert nationality_is_saudi([None, "", "   "]) == [None, None, None]


def test_unrecognised_value_raises_and_never_defaults():
    with pytest.raises(DerivationError) as exc:
        nationality_is_saudi(["Saudi", "Martian", "Atlantean"])
    msg = str(exc.value)
    assert "Martian" in msg and "Atlantean" in msg
    assert "Refusing to guess" in msg


def test_registry_resolution_and_unknown_rule():
    assert resolve("nationality_is_saudi") is nationality_is_saudi
    with pytest.raises(DerivationError) as exc:
        resolve("definitely_not_a_rule")
    assert "Unknown derivation rule" in str(exc.value)


def test_derivations_are_never_evaluated_as_expressions():
    # A contract is operator-supplied data. If a `derivation` value were ever
    # exec'd, a schema file would become an execution vector. Resolution must
    # be a registry lookup that rejects anything not registered by name.
    with pytest.raises(DerivationError):
        resolve("__import__('os').system('echo pwned')")
    assert all(callable(v) for v in REGISTRY.values())


def test_derive_column_uses_the_declared_rule():
    spec = {"name": "is_saudi", "derived_from": "nationality",
            "derivation": "nationality_is_saudi"}
    assert derive_column(spec, ["Saudi", "British"]) == [True, False]

    with pytest.raises(DerivationError):
        derive_column({"name": "is_saudi"}, ["Saudi"])


def test_contract_declares_the_derivation():
    """The employees contract must name a rule that exists in the registry."""
    import yaml
    sys.path.insert(0, os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))
    import canonical_schema

    col = next(c for c in canonical_schema.columns("employees")
               if c["name"] == "is_saudi")
    assert col["derived_from"] == "nationality"
    assert col["derivation"] in REGISTRY
    assert yaml is not None
