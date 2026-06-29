import yaml
import os

def generate_manifest():
    print("Generating synthetic dry-run manifest summary...")
    manifest_path = "config/synthetic_dry_run_manifest.yml"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for item in data.get("manifest", []):
            print(f"- Category: {item.get('source_category')} | File: {item.get('file_name')}")
    print("Manifest generation complete.")

if __name__ == "__main__":
    generate_manifest()
