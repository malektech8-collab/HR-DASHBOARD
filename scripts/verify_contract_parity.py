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

Run once before a change and once after; the two JSON results must be
byte-identical, including error strings.

It ALSO records each table's column inventory (names, in contract order,
plus the required subset). This closes a blind spot in the case-based design:
every case is built from the same contract it is validated against, so a
contract that has silently LOST a column stays self-consistent and every case
still passes. An absence is invisible to behaviour testing. The inventory is
compared directly, and `compare` exits non-zero if any column disappeared.

Usage:
    verify_contract_parity.py <label> [contracts_dir]     capture a run
    verify_contract_parity.py compare <before.json> <after.json>

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


def _parse_renames(argv):
    """--expect-rename table.old:table.new (repeatable).

    A rename is a removal plus an addition, which `compare` would otherwise
    report as a dropped column and fail. Declaring it puts the intent on the
    record instead of overriding the check. An UNDECLARED removal still fails.
    """
    renames = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--expect-rename":
            if i + 1 >= len(argv):
                raise SystemExit("--expect-rename needs table.old:table.new")
            spec = argv[i + 1]
            try:
                old, new = spec.split(":", 1)
                t_old, c_old = old.rsplit(".", 1)
                t_new, c_new = new.rsplit(".", 1)
            except ValueError:
                raise SystemExit("bad --expect-rename {!r}; want table.old:table.new".format(spec))
            if t_old != t_new:
                raise SystemExit("--expect-rename must stay within one table")
            renames.setdefault(t_old, {})[c_old] = c_new
            i += 2
        else:
            i += 1
    return renames


def compare(before_path, after_path, renames=None):
    """Diff two captured runs. Returns a process exit code.

    A DROPPED column is treated as a hard failure: it is the failure mode the
    behaviour cases structurally cannot see, and it silently shrinks the
    contract that every downstream consumer (template, labels, validation)
    reads.
    """
    with io.open(before_path, encoding="utf-8") as f:
        before = json.load(f)
    with io.open(after_path, encoding="utf-8") as f:
        after = json.load(f)

    # Tolerate runs captured before the inventory was added.
    renames = renames or {}
    b_inv = before.get("inventory", {})
    a_inv = after.get("inventory", {})
    b_cases = before.get("cases", before)
    a_cases = after.get("cases", after)
    if not b_inv or not a_inv:
        print("WARNING: one input predates inventory capture; "
              "column-inventory comparison skipped.")

    failed = False

    print("== column inventory ==")
    for t in sorted(set(b_inv) | set(a_inv)):
        bcols = b_inv.get(t, {}).get("columns", [])
        acols = a_inv.get(t, {}).get("columns", [])
        removed = [c for c in bcols if c not in acols]
        added = [c for c in acols if c not in bcols]
        declared = renames.get(t, {})
        honoured = [(o, n) for o, n in declared.items()
                    if o in removed and n in added]
        for o, n in honoured:
            removed.remove(o)
            added.remove(n)
            print("  {:<12} RENAMED {} -> {}  (declared)".format(t, o, n))
        reordered = (not removed and not added and bcols != acols)
        if removed:
            failed = True
            print("  {:<12} DROPPED {}  <-- FAILURE".format(t, removed))
        if added:
            print("  {:<12} added   {}".format(t, added))
        if reordered:
            print("  {:<12} REORDERED (same set, different order)".format(t))
        if not removed and not added and not reordered:
            print("  {:<12} unchanged ({} columns)".format(t, len(acols)))
    for t in sorted(set(b_inv) - set(a_inv)):
        failed = True
        print("  {:<12} TABLE MISSING ENTIRELY  <-- FAILURE".format(t))

    print("== case outcomes ==")
    diffs = 0
    for t in sorted(set(b_cases) | set(a_cases)):
        for c in sorted(set(b_cases.get(t, {})) | set(a_cases.get(t, {}))):
            bb = b_cases.get(t, {}).get(c)
            aa = a_cases.get(t, {}).get(c)
            if bb == aa:
                continue
            diffs += 1
            bo = (bb or {}).get("outcome")
            ao = (aa or {}).get("outcome")
            kind = "OUTCOME CHANGED" if bo != ao else "error string only"
            print("  {:<12} {:<30} {} -> {}  ({})".format(t, c, bo, ao, kind))
    if not diffs:
        print("  all cases identical")

    print("== verdict ==")
    if failed:
        print("  FAIL - a column or table was dropped")
        return 1
    print("  PASS - no column or table lost ({} case difference(s))".format(diffs))
    return 0


def main():
    global CONTRACTS_DIR
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    if len(sys.argv) > 2:
        CONTRACTS_DIR = sys.argv[2]
    print("contracts: {}".format(CONTRACTS_DIR))
    os.makedirs(CASES_DIR, exist_ok=True)
    results = {}
    inventory = {}
    for t in TABLES:
        cols = contract(t)
        # Recorded independently of any test case, so a dropped column shows up
        # even though the behaviour cases would remain self-consistent.
        inventory[t] = {
            "columns": [c["name"] for c in cols],
            "count": len(cols),
            "required": [c["name"] for c in cols if c.get("required")],
        }
        results[t] = {}
        for case_name, path in build_cases(t).items():
            results[t][case_name] = run(path, t)
    out = os.path.join(SCRATCH, "parity_{}.json".format(label))
    payload = {"inventory": inventory, "cases": results}
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)

    total = sum(len(v) for v in results.values())
    acc = sum(1 for t in results for c in results[t]
              if results[t][c]["outcome"] == "ACCEPT")
    rej = sum(1 for t in results for c in results[t]
              if results[t][c]["outcome"] == "REJECT")
    err = total - acc - rej
    ncols = sum(v["count"] for v in inventory.values())
    print("[{}] cases={} accept={} reject={} error={} | columns={} across {} tables"
          .format(label, total, acc, rej, err, ncols, len(inventory)))
    for t in TABLES:
        print("  inventory   {:<12} {} columns".format(t, inventory[t]["count"]))
    print("written: {}".format(out))
    for t in TABLES:
        for c in sorted(results[t]):
            print("  {:<12} {:<34} {}".format(t, c, results[t][c]["outcome"]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        if len(sys.argv) != 4:
            print("usage: verify_contract_parity.py compare <before.json> <after.json>")
            sys.exit(2)
        sys.exit(compare(sys.argv[2], sys.argv[3], _parse_renames(sys.argv[4:])))
    main()
