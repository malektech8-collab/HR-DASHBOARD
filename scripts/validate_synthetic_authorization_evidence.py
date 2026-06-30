from __future__ import annotations

from pathlib import Path
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "data" / "synthetic_dry_run" / "evidence"
SCHEMA_PATH = ROOT / "config" / "authorization_evidence_validation_schema_3k.yml"
REPORT_PATH = ROOT / "docs" / "qa" / "reports" / "milestone_3k_synthetic_evidence_dry_run_report.md"
REFUSED_FRAGMENTS = ("data/real_", ".env", "credentials", "secret", "token", "password")


def normalized(path: Path) -> str:
    return path.as_posix().lower()


def assert_safe_path(path: Path) -> None:
    resolved = path.resolve()
    evidence_root = EVIDENCE_DIR.resolve()
    if not (resolved == evidence_root or evidence_root in resolved.parents):
        raise ValueError(f"Refusing path outside synthetic evidence directory: {path}")
    lowered = normalized(path)
    for fragment in REFUSED_FRAGMENTS:
        if fragment in lowered:
            raise ValueError(f"Refusing unsafe path fragment '{fragment}': {path}")


def load_yaml(path: Path) -> dict:
    assert_safe_path(path)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def validate_file(path: Path, schema: dict) -> tuple[str, list[str]]:
    data = load_yaml(path)
    reasons: list[str] = []

    for field in schema["required_fields"]:
        if field not in data:
            reasons.append(f"missing field: {field}")

    if data.get("evidence_id") not in schema["allowed_evidence_ids"]:
        reasons.append("invalid evidence_id")
    if data.get("signatory_role") not in schema["allowed_signatory_roles"]:
        reasons.append("invalid signatory_role")
    if data.get("evidence_status") not in schema["allowed_statuses"]:
        reasons.append("invalid evidence_status")
    if data.get("evidence_source") != schema["required_evidence_source"]:
        reasons.append("evidence_source is not Synthetic Only")
    if data.get("approved_source_category") != schema["approved_source_category"]:
        reasons.append("approved_source_category is not allowed")
    defaults = schema["required_defaults"]
    if data.get("decision_recommendation") != defaults["decision_recommendation"]:
        reasons.append("decision_recommendation must remain Hold")
    if data.get("real_data_execution") != defaults["real_data_execution"]:
        reasons.append("real_data_execution must remain Not Approved")
    if data.get("load_scheduling") != defaults["load_scheduling"]:
        reasons.append("load_scheduling must remain Not Approved")
    if data.get("stop_criteria_count") != schema["stop_criteria_count"]:
        reasons.append("stop_criteria_count mismatch")

    present_fields = set(data.get("included_fields", []) or [])
    rejected_fields = set(schema["rejected_fields"])
    restricted = sorted(present_fields & rejected_fields)
    if restricted:
        reasons.append(f"restricted fields present: {', '.join(restricted)}")

    result = "pass" if not reasons else "reject"
    return result, reasons


def write_report(rows: list[dict]) -> None:
    passed = [row for row in rows if row["actual"] == "pass"]
    rejected = [row for row in rows if row["actual"] == "reject"]
    expected_ok = all(row["expected"] == row["actual"] for row in rows)

    lines = [
        "# Milestone 3K - Synthetic Evidence Dry-Run Report",
        "",
        "**Validation Scope**: Synthetic evidence files only.",
        "**Input Directory**: `data/synthetic_dry_run/evidence/`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total synthetic evidence files | {len(rows)} |",
        f"| Passed files | {len(passed)} |",
        f"| Rejected files | {len(rejected)} |",
        f"| Negative test cases rejected as expected | {'Yes' if expected_ok else 'No'} |",
        "",
        "## File Results",
        "",
        "| File | Expected | Actual | Rejection Reasons |",
        "|------|----------|--------|-------------------|",
    ]
    for row in rows:
        reasons = "; ".join(row["reasons"]) if row["reasons"] else "N/A"
        lines.append(f"| `{row['file']}` | {row['expected']} | {row['actual']} | {reasons} |")
    lines.extend([
        "",
        "## Governance Confirmation",
        "",
        "- Synthetic validation results do not update or imply real authorization evidence approval.",
        "- Real evidence remains `Not Provided`.",
        "- Decision recommendation remains `Hold`.",
        "- Real-data execution remains `Not Approved`.",
        "- Load scheduling remains `Not Approved`.",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    schema_wrapper = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = schema_wrapper["authorization_evidence_validation_schema_3k"]
    assert_safe_path(EVIDENCE_DIR)
    files = sorted(EVIDENCE_DIR.glob("*.yml"))
    rows = []
    for path in files:
        result, reasons = validate_file(path, schema)
        expected = load_yaml(path).get("expected_outcome")
        rows.append({
            "file": path.relative_to(ROOT).as_posix(),
            "expected": expected,
            "actual": result,
            "reasons": reasons,
        })
    write_report(rows)
    if not rows or any(row["expected"] != row["actual"] for row in rows):
        return 1
    print(f"Synthetic evidence validation passed: {len(rows)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
