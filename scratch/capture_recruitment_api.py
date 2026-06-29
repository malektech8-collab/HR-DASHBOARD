import urllib.request
import json
import os

endpoints = {
    "GET /api/recruitment/summary": "/api/recruitment/summary",
    "GET /api/recruitment/pipeline": "/api/recruitment/pipeline",
    "GET /api/recruitment/trends": "/api/recruitment/trends",
    "GET /api/recruitment/by-project": "/api/recruitment/by-project",
    "GET /api/recruitment/by-department": "/api/recruitment/by-department",
    "GET /api/recruitment/time-to-fill": "/api/recruitment/time-to-fill",
    "GET /api/recruitment/source-effectiveness": "/api/recruitment/source-effectiveness",
    "GET /api/recruitment/offers": "/api/recruitment/offers",
    "GET /api/recruitment/onboarding": "/api/recruitment/onboarding",
    "GET /api/recruitment/workforce-plan": "/api/recruitment/workforce-plan",
    "GET /api/recruitment/exceptions": "/api/recruitment/exceptions"
}

outputs = {}

for name, endpoint in endpoints.items():
    url = f"http://127.0.0.1:8000{endpoint}"
    try:
        req = urllib.request.urlopen(url)
        outputs[name] = json.loads(req.read().decode())
        print(f"Captured {name}")
    except Exception as e:
        print(f"Failed to capture {name}: {e}")

os.makedirs("docs/qa/api_outputs", exist_ok=True)
with open("docs/qa/api_outputs/milestone_2f_recruitment_api_outputs.json", "w", encoding="utf-8") as f:
    json.dump(outputs, f, indent=2)

print("Saved raw API JSON successfully.")
