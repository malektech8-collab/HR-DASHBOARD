# -*- coding: utf-8 -*-
"""The suite runs against its OWN data root. It never writes the operator's.

WHAT THIS FIXES, measured on the first real load: four tests of 536 wrote to
operator-owned state. `test_data::test_refresh_trigger` rebuilt the warehouse
in demo mode and rewrote the onboarding registry; three tests in
`test_contract_exceptions` called `ingest_raw.ingest()` directly. A full run
mutated 11 artefacts and deleted a twelfth.

The damage was never the warehouse - that rebuilds from data/raw in ninety
seconds. It was the registry, which came out INTERNALLY INCONSISTENT: a real
client's `declared` and `history_since` beside demo's `absent_columns`. That
flips `provides_column()` to True and silently returns thousands of suppressed
warnings to a client's Data Quality page.

WHY AN ENV VAR AND NOT monkeypatch/tmp_path. `test_refresh_trigger` POSTs
/api/data/refresh, and the API runs `refresh_all.py` as a SUBPROCESS. A
monkeypatch lives in this process and cannot cross that boundary, so the worst
offender is precisely the one a fixture cannot reach. `HRDASH_DATA_ROOT` is
inherited by the child, and by dbt below it.

WHY IT IS SET AT IMPORT TIME, not in a fixture. `settings.DATABASE_PATH` is a
pydantic field whose default is computed when `app.config` is imported. A
session fixture runs after test modules are imported, which is too late.
conftest is imported first, so this is the only point that is early enough.

WHY THE ROOT IS BUILT RATHER THAN COPIED. Copying the repo's `data/` would
copy a CLIENT'S REAL DATA into a temp directory on any operator machine. The
suite builds a demo dataset instead: deterministic, synthetic, and identical
on every machine regardless of what the operator has loaded.

That build is also what makes `test_demo_gate` self-sufficient. It used to
pass only because `test_data.py` sorts before `test_demo_gate.py` and rebuilt
the warehouse in demo mode as a side effect. Isolating writes without this
would have turned the demo fingerprint into a silent no-op - a gate reporting
success while asserting nothing.
"""
import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Default to a stable directory so successive local runs reuse the built
# warehouse. Honour an explicit override, which is what the CI isolation step
# and any ad-hoc debugging use.
_TEST_ROOT = os.environ.setdefault(
    "HRDASH_DATA_ROOT", os.path.join(_ROOT, ".pytest-data-root"))

# The suite is a DEMO suite. Set before any module reads it, for the same
# import-time reason as the root itself.
os.environ["DATA_MODE"] = "demo"
# PINNED, not merely unset. The operator's .env carries REPORT_MONTH for the
# real load, and report_period reads that FILE - so popping the variable is not
# enough and two contract-exception tests failed on the operator's machine and
# nowhere else. GAP-002's benign form, closed here.
os.environ["REPORT_MONTH"] = "2026-06"

_WAREHOUSE = os.path.join(_TEST_ROOT, "warehouse", "hr_analytics.duckdb")


def _stale():
    """Rebuild when the warehouse is missing, forced, or older than the code.

    An mtime comparison rather than a hash: cheap, and wrong only in the
    direction of rebuilding more often than strictly needed.
    """
    if os.environ.get("HRDASH_REBUILD_TEST_ROOT") == "1":
        return True
    if not os.path.exists(_WAREHOUSE):
        return True
    built = os.path.getmtime(_WAREHOUSE)
    for folder in (os.path.join(_ROOT, "scripts"),
                   os.path.join(_ROOT, "dbt_analytics", "models"),
                   os.path.join(_ROOT, "data", "contracts")):
        for base, _dirs, files in os.walk(folder):
            for name in files:
                if name.endswith((".py", ".sql", ".yml")):
                    if os.path.getmtime(os.path.join(base, name)) > built:
                        return True
    return False


# Sub-directories tests WRITE into. The built root is reused between runs for
# speed, so anything a test leaves here would outlive it - and did: a mapping
# profile written by test_mapping_api survived into test_upload_flow and turned
# its preview un-committable. Cleared at session start; not rebuilt, because
# nothing generates them.
_VOLATILE = ("mapping", "staging")


@pytest.fixture(scope="session", autouse=True)
def isolated_data_root():
    """Build the suite's own demo warehouse once, then hand it to every test."""
    os.makedirs(_TEST_ROOT, exist_ok=True)
    for name in _VOLATILE:
        shutil.rmtree(os.path.join(_TEST_ROOT, "data", name), ignore_errors=True)
    if _stale():
        env = dict(os.environ)
        env["HRDASH_DATA_ROOT"] = _TEST_ROOT
        env["DATA_MODE"] = "demo"
        env["REPORT_MONTH"] = "2026-06"
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, os.path.join(_ROOT, "scripts", "refresh_all.py")],
            cwd=_ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(
                "could not build the isolated test data root.\n"
                + (result.stdout or "")[-3000:]
                + (result.stderr or "")[-3000:])
    yield _TEST_ROOT
