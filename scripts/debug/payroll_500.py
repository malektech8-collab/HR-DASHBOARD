import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/payroll/summary") as r:
        print("Success:", r.read().decode())
except Exception as e:
    if hasattr(e, 'read'):
        print("Error response:", e.read().decode())
    else:
        print("Error:", e)
