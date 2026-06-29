"""
Capture Milestone 2G Talent Dashboard API outputs and screenshot for QA.
"""
import urllib.request
import json
import os

API_BASE = "http://127.0.0.1:8000/api/talent"

ENDPOINTS = [
    ("summary", "GET /api/talent/summary"),
    ("performance-distribution", "GET /api/talent/performance-distribution"),
    ("trends", "GET /api/talent/trends"),
    ("by-project", "GET /api/talent/by-project"),
    ("by-department", "GET /api/talent/by-department"),
    ("goals", "GET /api/talent/goals"),
    ("competency-gaps", "GET /api/talent/competency-gaps"),
    ("learning", "GET /api/talent/learning"),
    ("succession", "GET /api/talent/succession"),
    ("succession-readiness", "GET /api/talent/succession-readiness"),
    ("risk", "GET /api/talent/risk"),
    ("exceptions", "GET /api/talent/exceptions"),
]

results = {}
for path, label in ENDPOINTS:
    url = f"{API_BASE}/{path}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
            results[label] = data
            print(f"OK  {label}")
    except Exception as e:
        results[label] = {"error": str(e)}
        print(f"FAIL {label}: {e}")

out_path = r"docs\qa\api_outputs\milestone_2g_talent_api_outputs.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nSaved API outputs to {out_path}")
