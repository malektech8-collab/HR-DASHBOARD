import urllib.request
import json

endpoints = [
    "/api/recruitment/summary",
    "/api/recruitment/pipeline",
    "/api/recruitment/trends",
    "/api/recruitment/by-project",
    "/api/recruitment/by-department",
    "/api/recruitment/time-to-fill",
    "/api/recruitment/source-effectiveness",
    "/api/recruitment/offers",
    "/api/recruitment/onboarding",
    "/api/recruitment/workforce-plan",
    "/api/recruitment/exceptions"
]

for endpoint in endpoints:
    url = f"http://127.0.0.1:8000{endpoint}"
    try:
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode())
        print(f"SUCCESS: {endpoint} -> keys: {list(data.keys()) if isinstance(data, dict) else len(data)}")
    except Exception as e:
        print(f"FAILED: {endpoint} -> {e}")
