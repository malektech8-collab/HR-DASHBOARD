# -*- coding: utf-8 -*-
"""Assert that a full test run leaves operator-owned state untouched.

WHY THIS IS A JOB STEP AND NOT A TEST.

    "A full suite run does not write here" is a statement ABOUT a suite run.
    No test inside that run can make it: the writes it must observe happen in
    sibling tests, in arbitrary order, and some in subprocesses. The assertion
    has to live outside, which means a second invocation.

    That is the whole distinction this cycle records alongside GAP-002:

        CI can verify the MECHANISM - that paths resolve through the state
        root, that a redirected run writes only inside it.

        CI cannot verify the GUARANTEE from inside the suite. It needs a
        second invocation, and that invocation is this script.

WHY IT WORKS IN CI DESPITE CI HAVING NO REAL DATA.

    The bytes CI protects are synthetic, but the PROPERTY is about paths, not
    about data: "the suite does not write to the repository's data root" is
    true or false regardless of whose rows are in it. So the operator-only
    failure becomes CI-visible, which is exactly what GAP-002 says this family
    lacks.

USAGE
    python scripts/check_test_isolation.py            # snapshot, run, compare
    python scripts/check_test_isolation.py --verify-detects
        # sanity: prove the checker itself can FAIL, by writing to the
        # protected root on purpose. Per SP-001 a guard nobody has watched
        # fail is not a guard.
"""
import argparse
import hashlib
import os
import subprocess
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Everything the suite was measured writing before isolation: 11 mutated and
# one deleted. Directories are walked, so a NEW file appearing is caught too -
# the failure mode is not only "changed" but "created".
PROTECTED = [
    os.path.join("data", "onboarding"),
    os.path.join("data", "raw"),
    os.path.join("data", "bronze"),
    os.path.join("data", "silver"),
    os.path.join("data", "gold"),
    os.path.join("data", "mapping"),
    os.path.join("data", "staging"),
    "warehouse",
]


def _digest():
    """path -> md5, for every file under every protected directory."""
    out = {}
    for relative in PROTECTED:
        base = os.path.join(_ROOT, relative)
        if not os.path.isdir(base):
            continue
        for folder, _dirs, files in os.walk(base):
            for name in sorted(files):
                full = os.path.join(folder, name)
                try:
                    with open(full, "rb") as handle:
                        out[os.path.relpath(full, _ROOT)] = hashlib.md5(
                            handle.read()).hexdigest()
                except OSError:
                    # Unreadable is still a state we can compare against.
                    out[os.path.relpath(full, _ROOT)] = "<unreadable>"
    return out


def _compare(before, after):
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    removed = sorted(k for k in before if k not in after)
    created = sorted(k for k in after if k not in before)
    return changed, removed, created


def _run_suite():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    # Deliberately NOT setting HRDASH_DATA_ROOT: conftest picks its own default.
    # Forcing one here would prove the checker's variable works rather than
    # that the suite isolates itself, which is the thing under test.
    return subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests", "-q"],
        cwd=_ROOT, env=env).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-detects", action="store_true",
                        help="prove the checker can fail (SP-001)")
    args = parser.parse_args(argv)

    print("snapshotting operator-owned state...")
    before = _digest()
    print("  {} file(s) under {} protected path(s)".format(
        len(before), len(PROTECTED)))

    if args.verify_detects:
        # The tamper. Write into the protected root exactly as an unisolated
        # test would, and require the comparison below to notice.
        probe = os.path.join(_ROOT, "data", "onboarding",
                             "__isolation_probe__.yml")
        os.makedirs(os.path.dirname(probe), exist_ok=True)
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("# deliberate regression, written by --verify-detects\n")
        print("  wrote a deliberate regression: {}".format(
            os.path.relpath(probe, _ROOT)))
        after = _digest()
        changed, removed, created = _compare(before, after)
        os.remove(probe)
        if created:
            print("\nDETECTED: {}".format(", ".join(created)))
            print("the checker fails when the suite writes here. Good.")
            return 0
        print("\nNOT DETECTED - the checker cannot see a write it was built "
              "to catch, so a green run below would mean nothing.")
        return 1

    code = _run_suite()
    print("\npytest exited {}".format(code))

    after = _digest()
    changed, removed, created = _compare(before, after)

    if changed or removed or created:
        print("\nFAILED - the suite wrote to operator-owned state:")
        for group, items in (("CHANGED", changed), ("DELETED", removed),
                             ("CREATED", created)):
            for item in items:
                print("  {:<8} {}".format(group, item))
        print("\nA test must write only under HRDASH_DATA_ROOT. See "
              "backend/tests/conftest.py and scripts/paths.py.")
        return 1

    print("PASSED - {} file(s) byte-identical; the suite wrote nothing "
          "outside its own root.".format(len(before)))
    # The suite's own result still decides the build.
    return code


if __name__ == "__main__":
    sys.exit(main())
