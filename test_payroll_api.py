import urllib.request
import json
import sys

def test_api():
    print("Testing Payroll API endpoints...")
    
    urls = {
        'summary': 'http://127.0.0.1:8000/api/payroll/summary',
        'components': 'http://127.0.0.1:8000/api/payroll/components',
        'trends': 'http://127.0.0.1:8000/api/payroll/trends',
        'by-project': 'http://127.0.0.1:8000/api/payroll/by-project',
        'by-department': 'http://127.0.0.1:8000/api/payroll/by-department',
        'variance': 'http://127.0.0.1:8000/api/payroll/variance',
        'exceptions': 'http://127.0.0.1:8000/api/payroll/exceptions'
    }
    
    success = True
    for name, url in urls.items():
        try:
            req = urllib.request.urlopen(url)
            code = req.getcode()
            body = req.read().decode("utf-8")
            data = json.loads(body)
            print(f"  [OK] {name} endpoint responded with {code}")
        except Exception as e:
            print(f"  [ERROR] {name} endpoint failed: {e}")
            success = False
            
    if not success:
        print("Payroll API tests FAILED.")
        sys.exit(1)
    else:
        print("Payroll API tests PASSED.")

if __name__ == "__main__":
    test_api()
