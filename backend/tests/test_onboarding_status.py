"""GET /api/data/onboarding-status — the checklist behind the onboarding screen.

A read of `domain_provenance`, which build_warehouse already writes. No new
computation: the facts existed and had nowhere to be seen.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.main import app  # noqa: E402

client = TestClient(app)


def auth():
    from app.core.security import MOCK_USER_DB

    email = next(iter(MOCK_USER_DB))
    token = client.post("/api/governance/token",
                        data={"username": email,
                              "password": MOCK_USER_DB[email]["hashed_password"]}
                        ).json()["access_token"]
    return {"Authorization": "Bearer {}".format(token)}


@pytest.fixture(scope="module")
def status():
    response = client.get("/api/data/onboarding-status", headers=auth())
    assert response.status_code == 200, response.text
    return response.json()


def test_it_requires_authentication():
    assert client.get("/api/data/onboarding-status").status_code == 401


def test_every_contracted_domain_appears(status):
    import canonical_schema as cs

    reported = {d["domain"] for d in status["domains"]}
    assert set(cs.available_tables()) <= reported


def test_the_uncontracted_domains_are_UNAVAILABLE_not_merely_missing(status):
    """A client shown 'missing' for a domain they cannot provide will keep
    trying to upload it."""
    uncontracted = [d for d in status["domains"] if not d["contracted"]]
    assert uncontracted, "expected recruitment/talent from domain_provenance"
    for domain in uncontracted:
        assert domain["available"] is False
        assert domain["unavailable_reason"]
        assert "no contract" in domain["unavailable_reason"].lower()


def test_contracted_domains_are_uploadable(status):
    for domain in status["domains"]:
        if domain["contracted"]:
            assert domain["available"] is True
            assert domain["unavailable_reason"] is None


def test_labels_are_bilingual_and_come_from_the_contract(status):
    employees = next(d for d in status["domains"] if d["domain"] == "employees")
    assert employees["label_en"]
    assert employees["label_ar"]
    assert employees["label_en"] != employees["label_ar"]


def test_demo_reports_every_domain_as_provided(status):
    """Demo IS sample data, so the checklist is complete - which is also what
    keeps the demo gate unchanged."""
    assert status["data_mode"] == "demo"
    assert all(d["provided"] for d in status["domains"])


def test_it_carries_the_reporting_period(status):
    assert status["report_month"]


def test_coverage_is_reported_for_the_date_grained_domain(status):
    """Full coverage in demo, so covered == expected and the UI shows no note."""
    attendance = next(d for d in status["domains"] if d["domain"] == "attendance")
    assert attendance["covered_days"] == attendance["expected_days"]


class _NoTable:
    def execute(self, *_a, **_kw):
        raise RuntimeError("no such table: domain_provenance")


def test_a_warehouse_without_the_table_reports_nothing_rather_than_inventing():
    """An older warehouse, or one whose build aborted. Same default-deny as
    step 2b: report no state rather than a guessed one."""
    from app.api.data import get_onboarding_status

    result = get_onboarding_status(conn=_NoTable(), current_user={"email": "t"})
    assert all(d.provided is False for d in result.domains)
    assert all(d.row_count == 0 for d in result.domains)
