import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add backend to python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app.main import app

client = TestClient(app)

from app.core.security import MOCK_USER_DB

def test_governance_status_endpoint():
    # Authenticate as SYSTEM_ADMIN to access governance status
    login_response = client.post(
        "/api/governance/token",
        data={"username": "admin@synthetic.local", "password": MOCK_USER_DB["admin@synthetic.local"]["hashed_password"]}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/governance/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    data = response.json()

    # Assert mandatory fields exist
    required_keys = [
        "current_gate",
        "current_status",
        "evidence_status",
        "synthetic_validation_status",
        "decision_recommendation",
        "real_data_execution_approved",
        "real_authorization_evidence_approved",
        "load_scheduling_approved",
        "go_no_go_meeting_held",
        "stop_criteria_count",
        "last_completed_milestone",
        "milestone_3i_status",
        "milestone_3j_status",
        "milestone_3k_status"
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"

    # Assert exact governance values
    assert data["current_gate"] == "Gate 5 - Authorization Evidence Pending"
    assert data["current_status"] == "Authorization Evidence Pending"
    assert data["evidence_status"] == "Not Provided"
    assert data["synthetic_validation_status"] == "Synthetic Validation Only"
    assert data["decision_recommendation"] == "Hold"

    # Assert strict non-approval safety bounds
    assert data["real_data_execution_approved"] is False
    assert data["real_authorization_evidence_approved"] is False
    assert data["load_scheduling_approved"] is False
    assert data["go_no_go_meeting_held"] is False

    # Assert stop criteria and milestone constraints
    assert data["stop_criteria_count"] == 22
    assert data["last_completed_milestone"] == "3K"
    assert data["milestone_3i_status"] == "Authorization Evidence Pending"
    assert data["milestone_3j_status"] == "Planning Only"
    assert data["milestone_3k_status"] == "Synthetic Validation Only"
