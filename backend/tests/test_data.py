import sys
import os
import shutil
import pytest
from fastapi.testclient import TestClient

# Add backend to python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from app.main import app
from app.api.data import get_silver_dir

client = TestClient(app)


def auth_headers():
    """P0-2 step 1c: upload and refresh now require an authenticated operator.

    The synthetic-JWT layer itself is untouched and logged as Phase 3
    hardening; this only exercises the login the app already ships.
    """
    from app.core.security import MOCK_USER_DB

    email = next(iter(MOCK_USER_DB))
    token = client.post(
        "/api/governance/token",
        data={"username": email,
              "password": MOCK_USER_DB[email]["hashed_password"]},
    ).json()["access_token"]
    return {"Authorization": "Bearer {}".format(token)}


# The upload tests moved to test_upload_flow.py when the endpoint became a
# staged flow (P0-2). Auth, the parquet refusal and the explicit table are
# all covered there, against the endpoints that now exist.


def test_refresh_trigger():
    # Trigger pipeline refresh via subprocess
    response = client.post("/api/data/refresh", headers=auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "return_code" in data
    assert "stdout" in data
    assert "stderr" in data
