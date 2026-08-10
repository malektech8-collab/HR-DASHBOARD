# -*- coding: utf-8 -*-
"""Accept/reject parity harness for the canonical-schema extension.

CI never exercises the contracts (they are only read on the real path), so CI
passing is NOT evidence the extension is safe. This harness is.

For each contracted table it builds five synthetic CSVs and records the exact
outcome of validate_csv_against_contract for each:

  conformant           -> must ACCEPT
  missing-required     -> must REJECT (required-columns)
  unexpected-column    -> must REJECT (no-unexpected-columns)
  bad-type             -> must REJECT (type-conformance)
  bad-allowed-value    -> must REJECT (allowed-values)   [only where an enum exists]

Run once before the extension and once after; the two JSON results must be
byte-identical, including error strings.

No real data. All inputs are synthetic and written to a temporary directory.
"""
import io
import json
import os
import sys
import tempfile

os.chdir(r"D:\workspace\repos\HR-DASHBOARD")
sys.path.insert(0, os.path.abspath("scripts"))
import yaml  # noqa: E402
from validate_schema import validate_csv_against_contract, SchemaValidationError  # noqa: E402

SCRATCH = tempfile.mkdtemp(prefix="contract_parity_")
CASES_DIR = os.path.join(SCRATCH, "cases")
TABLES = ["employees", "payroll", "attendance", "compliance", "hr_requests"]

# Deterministic, type-appropriate synthetic values. Not real data.
SAMPLE_VALUE = {
    "VARCHAR": "X1",
    "INTEGER": "1",
    "DECIMAL": "1.5",
    "DATE": "2026-06-01",
    "TIMESTAMP": "2026-06-01 08:00:00",
    "BOOLEAN": "true",
}
BAD_VALUE = {
    "INTEGER": "not_an_int",
    "DECIMAL": "not_a_decimal",
    "DATE": "0025-01-26",          # the real-world corrupted-serial case
    "TIMESTAMP": "not_a_timestamp",
    "BOOLEAN": "maybe",
}


CONTRACTS_DIR = "data/contracts"


def contract(table):
    with io.open(os.path.join(CONTRACTS_DIR, "{}_schema.yml".format(table)), encoding="utf-8") as f:
        return yaml.safe_load(f)["columns"]


def value_for(col):
    allowed = col.get("allowed_values")
    if allowed:
        return allowed[0]
    return SAMPLE_VALUE.get(str(col.get("type", "VARCHAR")).upper(), "X1")


def write_csv(path, header, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(r) + "\n")


def run(csv_path, table):
    """Validate one case. The absolute case path is scrubbed from the recorded
    error so results are comparable across runs and machines — the harness
    compares semantics, not temp directory names."""
    try:
        validate_csv_against_contract(csv_path, table, contracts_dir=CONTRACTS_DIR)
        return {"outcome": "ACCEPT", "error": None}
    except SchemaValidationError as e:
        return {"outcome": "REJECT",
                "error": str(e).replace(csv_path, "<CASE_FILE>")}
    except Exception as e:  # any other failure is itself a finding
        return {"outcome": "ERROR", "error": "{}: {}".format(type(e).__name__, e)}


def build_cases(table):
    cols = contract(table)
    names = [c["name"] for c in cols]
    row = [value_for(c) for c in cols]
    cases = {}

    p = os.path.join(CASES_DIR, "{}__conformant.csv".format(table))
    write_csv(p, names, [row, row])
    cases["conformant"] = p

    required = [c["name"] for c in cols if c.get("required")]
    if required:
        drop = required[-1]
        idx = names.index(drop)
        p = os.path.join(CASES_DIR, "{}__missing_required.csv".format(table))
        write_csv(p, [n for n in names if n != drop],
                  [[v for i, v in enumerate(row) if i != idx]])
        cases["missing_required"] = p

    p = os.path.join(CASES_DIR, "{}__unexpected_column.csv".format(table))
    write_csv(p, names + ["surprise_column"], [row + ["Z"]])
    cases["unexpected_column"] = p

    typed = [c for c in cols if str(c.get("type", "VARCHAR")).upper() in BAD_VALUE]
    if typed:
        target = typed[0]
        idx = names.index(target["name"])
        bad = list(row)
        bad[idx] = BAD_VALUE[str(target["type"]).upper()]
        p = os.path.join(CASES_DIR, "{}__bad_type.csv".format(table))
        write_csv(p, names, [bad])
        cases["bad_type__{}".format(target["name"])] = p

    enum = [c for c in cols if c.get("allowed_values")]
    if enum:
        target = enum[0]
        idx = names.index(target["name"])
        bad = list(row)
        bad[idx] = "NOT_A_VALID_ENUM_VALUE"
        p = os.path.join(CASES_DIR, "{}__bad_enum.csv".format(table))
        write_csv(p, names, [bad])
        cases["bad_enum__{}".format(target["name"])] = p

    return cases


def main():
    global CONTRACTS_DIR
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    if len(sys.argv) > 2:
        CONTRACTS_DIR = sys.argv[2]
    print("contracts: {}".format(CONTRACTS_DIR))
    os.makedirs(CASES_DIR, exist_ok=True)
    results = {}
    for t in TABLES:
        results[t] = {}
        for case_name, path in build_cases(t).items():
            results[t][case_name] = run(path, t)
    out = os.path.join(SCRATCH, "parity_{}.json".format(label))
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, sort_keys=True)

    total = sum(len(v) for v in results.values())
    acc = sum(1 for t in results for c in results[t]
              if results[t][c]["outcome"] == "ACCEPT")
    rej = sum(1 for t in results for c in results[t]
              if results[t][c]["outcome"] == "REJECT")
    err = total - acc - rej
    print("[{}] cases={} accept={} reject={} error={}".format(label, total, acc, rej, err))
    print("written: {}".format(out))
    for t in TABLES:
        for c in sorted(results[t]):
            print("  {:<12} {:<34} {}".format(t, c, results[t][c]["outcome"]))


if __name__ == "__main__":
    main()
