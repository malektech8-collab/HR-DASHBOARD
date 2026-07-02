import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add backend to python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app.main import app
from app.core.security import MOCK_USER_DB

client = TestClient(app)

def test_login_success():
    """
    Test successful login for all mock users and check token structure.
    """
    for email, user_data in MOCK_USER_DB.items():
        response = client.post(
            "/api/governance/token",
            data={"username": email, "password": user_data["hashed_password"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

def test_login_failure():
    """
    Test login rejection for invalid passwords or nonexistent accounts.
    """
    response = client.post(
        "/api/governance/token",
        data={"username": "admin@synthetic.local", "password": "wrongpassword"}
    )
    assert response.status_code == 401

    response = client.post(
        "/api/governance/token",
        data={"username": "unknown@synthetic.local", "password": "somepassword"}
    )
    assert response.status_code == 401

def test_governance_access_granted():
    """
    Test that SYSTEM_ADMIN and EXECUTIVE mock users can successfully access governance status.
    """
    # 1. Test SYSTEM_ADMIN
    admin_login = client.post(
        "/api/governance/token",
        data={"username": "admin@synthetic.local", "password": MOCK_USER_DB["admin@synthetic.local"]["hashed_password"]}
    )
    admin_token = admin_login.json()["access_token"]

    response = client.get(
        "/api/governance/status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["current_status"] == "Authorization Evidence Pending"

    # 2. Test EXECUTIVE
    exec_login = client.post(
        "/api/governance/token",
        data={"username": "exec@synthetic.local", "password": MOCK_USER_DB["exec@synthetic.local"]["hashed_password"]}
    )
    exec_token = exec_login.json()["access_token"]

    response = client.get(
        "/api/governance/status",
        headers={"Authorization": f"Bearer {exec_token}"}
    )
    assert response.status_code == 200

def test_governance_access_forbidden():
    """
    Test that HR_ANALYST user receives a 403 Forbidden error.
    """
    hr_login = client.post(
        "/api/governance/token",
        data={"username": "hr@synthetic.local", "password": MOCK_USER_DB["hr@synthetic.local"]["hashed_password"]}
    )
    hr_token = hr_login.json()["access_token"]

    response = client.get(
        "/api/governance/status",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_governance_access_unauthorized():
    """
    Test that accessing the endpoint with no token returns 401 Unauthorized.
    """
    response = client.get("/api/governance/status")
    assert response.status_code == 401
