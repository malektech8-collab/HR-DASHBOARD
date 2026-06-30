import sys
import os
from fastapi.testclient import TestClient

# Add backend to python path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
)

from app.main import app

client = TestClient(app)

def test_api():
    print("Testing Talent API endpoints locally...")

    endpoints = [
        'summary', 'performance-distribution', 'trends', 'by-project', 'by-department',
        'goals', 'competency-gaps', 'learning', 'succession', 'succession-readiness',
        'risk', 'exceptions'
    ]

    success = True
    for ep in endpoints:
        try:
            res = client.get(f"/api/talent/{ep}")
            assert res.status_code == 200
            data = res.json()
            assert isinstance(data, dict) or isinstance(data, list)
            print(f"  [OK] {ep} endpoint responded with 200")
        except Exception as e:
            print(f"  [ERROR] {ep} endpoint failed: {e}")
            success = False

    assert success, "Talent API tests FAILED."

if __name__ == "__main__":
    test_api()
