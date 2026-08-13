# -*- coding: utf-8 -*-
"""The two routes the mapping screen uses.

    GET  /uploads/{id}/columns   the client's own columns, with sample values
    POST /mapping/{table}        append a version from the screen's decisions

The samples route is the one endpoint whose PURPOSE is to return client data.
It is separate from the preview for exactly that reason - so it is reviewable
as such, rather than hidden inside a response that everything calls.
"""
import io
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import canonical_schema as cs  # noqa: E402,F401
sys.path.insert(0, os.path.join(_ROOT, "backend"))

import mapping  # noqa: E402
from test_mapping_profiles import a_client_export, a_profile, label_ar  # noqa: E402


@pytest.fixture(autouse=True)
def _at_root(monkeypatch):
    monkeypatch.chdir(_ROOT)


from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

api = TestClient(app)


def _auth():
    from app.core.security import MOCK_USER_DB
    email = next(iter(MOCK_USER_DB))
    token = api.post("/api/governance/token",
                     data={"username": email,
                           "password": MOCK_USER_DB[email]["hashed_password"]}
                     ).json()["access_token"]
    return {"Authorization": "Bearer {}".format(token)}


@pytest.fixture
def staged_arabic(tmp_path, monkeypatch):
    """Stage the Arabic export and point profiles at a temp dir."""
    monkeypatch.setattr(mapping, "PROFILE_DIR", str(tmp_path))
    monkeypatch.setattr(mapping, "CONTAINER_PROFILE_DIR", str(tmp_path))
    body = a_client_export().write_csv().encode("utf-8")
    response = api.post("/api/data/uploads?table=employees",
                        files={"file": ("export.csv", body, "text/csv")},
                        headers=_auth())
    assert response.status_code == 200, response.text
    upload_id = response.json()["upload_id"]
    yield upload_id
    api.delete("/api/data/uploads/{}".format(upload_id), headers=_auth())


def test_both_mapping_routes_require_a_token(staged_arabic):
    assert api.get(
        "/api/data/uploads/{}/columns".format(staged_arabic)).status_code == 401
    assert api.post("/api/data/mapping/employees",
                    json={"upload_id": staged_arabic}).status_code == 401


def test_the_workspace_returns_their_columns_with_samples(staged_arabic):
    body = api.get("/api/data/uploads/{}/columns".format(staged_arabic),
                   headers=_auth()).json()
    assert body["table"] == "employees"
    assert len(body["source_columns"]) == 24
    by_header = {c["header"]: c for c in body["source_columns"]}
    # their own values, so a human can recognise the column
    assert by_header["الجنسيه"]["samples"], "a header alone often will not settle it"
    assert by_header["الجنسيه"]["candidates"][0]["matched_by"] == "label_normalised"
    assert by_header["ملاحظات"]["candidates"] == []
    assert body["reject_enum_consequences"]["end_of_service_type"]
    assert body["derivation_rules"] == ["nationality_is_saudi"]


def test_the_workspace_offers_every_canonical_target(staged_arabic):
    body = api.get("/api/data/uploads/{}/columns".format(staged_arabic),
                   headers=_auth()).json()
    offered = {c["name"] for c in body["canonical_columns"]}
    assert offered == {c["name"] for c in cs.columns("employees")}
    labels = {c["name"]: c for c in body["canonical_columns"]}
    assert labels["status"]["label_ar"], "bilingual, from the contract"
    assert labels["status"]["allowed_values"]


def test_saving_from_the_screen_writes_an_attributed_profile(staged_arabic, tmp_path):
    source = a_profile()
    decisions = [{"header": h, "decision": "mapped", "chosen": c, "reason": None}
                 for h, c in source["columns"].items()]
    decisions += [{"header": e["header"], "decision": "ignored",
                   "chosen": None, "reason": e["reason"]}
                  for e in source["ignored"]]
    response = api.post(
        "/api/data/mapping/employees",
        json={"upload_id": staged_arabic, "decisions": decisions,
              "values": source["values"], "derive": source["derive"],
              "confirmations": {"status": source["values"]["status"]}},
        headers=_auth())
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["mapped"], body["ignored"], body["undecided"]) == (22, 2, 0)
    assert body["created_by"], "taken from the session, not the body"

    version = mapping.load_profile("employees")
    assert len(version["evidence"]) == 24
    assert version["confirmations"]["status"]["confirmed_by"] == body["created_by"]


def test_the_screen_cannot_save_an_unaffirmed_value_mapping(staged_arabic):
    response = api.post(
        "/api/data/mapping/employees",
        json={"upload_id": staged_arabic,
              "decisions": [{"header": label_ar("employees", "employee_id"),
                             "decision": "mapped", "chosen": "employee_id",
                             "reason": None}],
              "values": {"status": {"معلق": "Active"}},
              "confirmations": {}},
        headers=_auth())
    assert response.status_code == 400
    assert "معلق" in response.text


def test_a_mapping_save_cannot_target_another_table(staged_arabic):
    response = api.post(
        "/api/data/mapping/payroll",
        json={"upload_id": staged_arabic, "decisions": []}, headers=_auth())
    assert response.status_code == 400
    assert "employees file" in response.text


def test_the_samples_route_is_the_only_one_that_returns_client_values():
    """The PII boundary, as a structural fact rather than an intention.

    Values leave the API in exactly two places: a violation message, which
    quotes the offending value because that is the point of it, and this route,
    whose whole purpose is recognition. Nothing writes them down.
    """
    source = io.open(os.path.join(_ROOT, "backend", "app", "api", "data.py"),
                     encoding="utf-8").read()
    workspace = source.split("def mapping_workspace")[1].split("def save_mapping")[0]
    assert "samples=distinct[:MAX_SAMPLES]" in workspace
    body = source.split("def save_mapping")[1]
    assert "samples" not in body, "a save must never carry values back"
    assert "distinct_values" not in body, "nor the vocabulary set"


def test_distinct_values_are_scoped_by_the_same_PII_predicate(staged_arabic):
    """The client must map their whole vocabulary, not five samples of it.

    A status column's words are the thing being mapped, so all of them are
    returned - five samples cannot show a word that first appears on row 900.
    A name column gets none, by the same predicate the PII rule uses at the
    write: a vocabulary's values are vocabulary, a person's are not. Both are
    display-only; neither is persisted.
    """
    body = api.get("/api/data/uploads/{}/columns".format(staged_arabic),
                   headers=_auth()).json()
    by_header = {c["header"]: c for c in body["source_columns"]}

    status = by_header[label_ar("employees", "status")]
    assert set(status["distinct_values"]) == {"نشط", "موقوف"}

    name = by_header[label_ar("employees", "employee_name") + " "]
    assert name["distinct_values"] == [], "a person's values are not a vocabulary"
    assert name["samples"], "five for recognition is still allowed"
