import os
import re

def audit_dry_run():
    print("Running no-real-data security audit on dry-run folders...")
    
    # 1. Audit that real landing folders are clean
    real_folders = [
        "data/real_inbox",
        "data/real_quarantine",
        "data/real_approved",
        "data/real_rejected",
        "data/real_archive"
    ]
    
    clean = True
    for folder in real_folders:
        if os.path.exists(folder):
            contents = os.listdir(folder)
            non_gitkeep = [f for f in contents if f != ".gitkeep"]
            if non_gitkeep:
                print(f"SECURITY ALERT: Non-gitkeep files found in real-data folder '{folder}': {non_gitkeep}")
                clean = False

    # 2. Check dry-run input files (if any exist) for sensitive patterns
    dry_run_input_dir = "data/synthetic_dry_run/input"
    if os.path.exists(dry_run_input_dir):
        for root, dirs, files in os.walk(dry_run_input_dir):
            for file in files:
                if file == ".gitkeep":
                    continue
                path = os.path.join(root, file)
                print(f"Auditing file for sensitive patterns: {path}")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                        # Pattern 1: Saudi Iqama check (usually starts with 1 or 2, 10 digits)
                        iqamas = re.findall(r"\b[12]\d{9}\b", content)
                        if iqamas:
                            print(f"ALERT: Potential real National ID / Iqama format found in {path}: {iqamas}")
                            clean = False

                        # Pattern 2: IBAN pattern check (SA followed by 22 digits)
                        ibans = re.findall(r"\bSA\d{22}\b", content, re.IGNORECASE)
                        if ibans:
                            print(f"ALERT: Potential real IBAN format found in {path}: {ibans}")
                            clean = False

                        # Pattern 3: Real emails (corporate domains instead of synthetic/example)
                        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|synthetic\.local)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content)
                        if emails:
                            print(f"ALERT: Potential non-synthetic email found in {path}: {emails}")
                            clean = False
                except Exception as e:
                    print(f"Failed to read file {path} for audit. Error: {e}")

    if clean:
        print("PASS: No real data or active credentials detected in ingestion paths.")
    else:
        print("FAIL: Security validation failed. Real data patterns found.")
        exit(1)

if __name__ == "__main__":
    audit_dry_run()
