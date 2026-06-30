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
    print("Testing Payroll API endpoints locally...")
    
    endpoints = [
        'summary',
        'components',
        'trends',
        'by-project',
        'by-department',
        'variance',
        'exceptions'
    ]
    
    success = True
    for name in endpoints:
        try:
            res = client.get(f"/api/payroll/{name}")
            assert res.status_code == 200
            data = res.json()
            assert isinstance(data, dict) or isinstance(data, list)
            print(f"  [OK] {name} endpoint responded with 200")
        except Exception as e:
            print(f"  [ERROR] {name} endpoint failed: {e}")
            success = False
            
    assert success, "Payroll API tests FAILED."

if __name__ == "__main__":
    test_api()
