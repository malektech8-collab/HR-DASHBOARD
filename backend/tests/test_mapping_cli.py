# -*- coding: utf-8 -*-
"""The operator CLI: authoring a profile with no browser.

Cycle B makes `build_version` the only sanctioned way to produce a version,
which deliberately breaks the cycle-A path of hand-writing YAML - today the
ONLY way a profile gets written at all. These pin the replacement: the
operator contract changes shape rather than vanishing.

The affirmation is never pre-filled here either. `--by` supplies the
ATTRIBUTION; the operator restating the pairs supplies the assent. A tool that
signed on the operator's behalf would be recording nothing.
"""
import io
import os
import subprocess
import sys

import pytest
import yaml

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import canonical_schema as cs  # noqa: E402,F401
import mapping  # noqa: E402
from test_mapping_profiles import a_client_export, a_profile, label_ar  # noqa: E402


@pytest.fixture(autouse=True)
def _at_root(monkeypatch):
    monkeypatch.chdir(_ROOT)


# --------------------------------------------------------------------------
# the CLI - the operator contract changes shape rather than vanishing
# --------------------------------------------------------------------------

def _cli(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, os.path.join(_ROOT, "scripts", "mapping_cli.py")]
        + list(args),
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=_ROOT)


@pytest.fixture
def client_csv(tmp_path):
    path = tmp_path / "export.csv"
    a_client_export().write_csv(path)
    return path


def test_the_cli_proposes_the_contract_matches_and_leaves_the_rest(client_csv, tmp_path):
    out = tmp_path / "decisions.yml"
    result = _cli("suggest", "--table", "employees",
                  "--file", str(client_csv), "--out", str(out))
    assert result.returncode == 0, result.stderr
    spec = yaml.safe_load(out.read_text(encoding="utf-8"))
    # 24, not 22: iqama_expiry and iqama_occupation moved onto the employees
    # contract, and this fixture carries every contract column under its Arabic
    # label - so the ladder now MAPS two columns a client was previously asked
    # to supply in a separate compliance file. That is the intended effect of
    # the move, not a drift.
    assert len(spec["columns"]) == 24
    assert spec["confirmations"] == {}, "the affirmation is never pre-filled"
    text = out.read_text(encoding="utf-8")
    assert "ملاحظات" in text, "the undecided ones are listed for the operator"
    assert "Article 80" in text, "the consequence travels with the decision"


def test_the_cli_refuses_an_unaffirmed_value_mapping(client_csv, tmp_path):
    decisions = tmp_path / "decisions.yml"
    decisions.write_text(yaml.safe_dump(
        {"columns": {label_ar("employees", "employee_id"): "employee_id"},
         "values": {"status": {"معلق": "Active"}}},
        allow_unicode=True), encoding="utf-8")
    result = _cli("save", "--table", "employees", "--file", str(client_csv),
                  "--decisions", str(decisions), "--by", "op@x",
                  "--path", str(tmp_path / "employees.yml"))
    assert result.returncode == 2
    assert "REFUSED" in result.stderr
    assert not (tmp_path / "employees.yml").exists()


def test_the_cli_writes_a_complete_profile_with_no_browser(client_csv, tmp_path):
    profile = tmp_path / "employees.yml"
    source = a_profile()
    decisions = tmp_path / "decisions.yml"
    decisions.write_text(yaml.safe_dump({
        "columns": source["columns"],
        "ignored": source["ignored"],
        "values": source["values"],
        "derive": source["derive"],
        "confirmations": {"status": {"pairs": source["values"]["status"]}},
    }, allow_unicode=True), encoding="utf-8")

    result = _cli("save", "--table", "employees", "--file", str(client_csv),
                  "--decisions", str(decisions), "--by", "operator@synthetic.local",
                  "--path", str(profile))
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Saudization" in result.stdout, "it states what is being affirmed"

    version = mapping.load_profile("employees", path=str(profile))
    assert version["created_by"] == "operator@synthetic.local"
    assert len(version["evidence"]) == 26, \
        "evidence by construction, not by memory"
    assert version["confirmations"]["status"]["confirmed_by"] == \
        "operator@synthetic.local"
    written = io.open(profile, encoding="utf-8").read()
    assert "X1" not in written, "the PII rule holds on the CLI path too"

    # and the profile it wrote actually works
    mapped, report = mapping.apply_profile(a_client_export(), "employees", version)
    assert report.unmapped == []
    assert "is_saudi" in mapped.columns


def test_the_cli_never_invents_an_affirmation(client_csv, tmp_path):
    """--by supplies the ATTRIBUTION. It must not also supply the assent: if
    the operator did not restate the pairs, nothing is affirmed."""
    decisions = tmp_path / "decisions.yml"
    decisions.write_text(yaml.safe_dump(
        {"columns": {label_ar("employees", "employee_id"): "employee_id"},
         "values": {"status": {"معلق": "Active"}},
         "confirmations": {}},
        allow_unicode=True), encoding="utf-8")
    result = _cli("save", "--table", "employees", "--file", str(client_csv),
                  "--decisions", str(decisions), "--by", "op@x",
                  "--path", str(tmp_path / "employees.yml"))
    assert result.returncode == 2
