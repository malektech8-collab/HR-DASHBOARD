import urllib.request
import json

endpoints = [
    'summary', 'performance-distribution', 'trends', 'by-project', 'by-department',
    'goals', 'competency-gaps', 'learning', 'succession', 'succession-readiness',
    'risk', 'exceptions'
]

for ep in endpoints:
    url = f"http://127.0.0.1:8000/api/talent/{ep}"
    try:
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
            keys = list(data.keys())
            print(f"OK  {ep}: keys={keys}")
    except Exception as e:
        print(f"FAIL {ep}: {e}")
