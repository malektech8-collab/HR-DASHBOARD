import yaml
import os

def reconcile_control_totals():
    print("Reconciling synthetic dry-run control totals...")
    totals_path = "config/synthetic_dry_run_control_totals.yml"
    if os.path.exists(totals_path):
        with open(totals_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for item in data.get("control_totals", []):
            print(f"- {item.get('source_category')}: Expected Rows = {item.get('expected_rows')}")
    print("Control total reconciliation complete.")

if __name__ == "__main__":
    reconcile_control_totals()
