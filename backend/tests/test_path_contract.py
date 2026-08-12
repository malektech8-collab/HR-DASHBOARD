"""Every `/api/...` the frontend names must be a route the backend serves.

THE DEFECT THIS EXISTS FOR, precisely:

  P0-2 deleted the route `/api/data/upload`. It did not touch `uploadFile()`,
  which kept its literal string. TypeScript was satisfied - the symbol existed
  and its types were fine. A component test of the Data Quality widget, mocking
  `useUploadMutation`, would have PASSED, because the mock does not know the
  route is gone. The widget stayed broken until a later cycle read the imports.

  It was a contract mismatch between two halves that never meet at compile
  time, which is exactly the boundary component tests mock. So it needs this,
  and this is the only test in the suite that would have caught it.

WHY THE MATCH RULE HAS ITS SHAPE - and this is the important part.

  Template literals like `/api/data/uploads/${id}` scan as the string
  `/api/data/uploads/`, which is in no OpenAPI path verbatim. So the rule needs
  a template allowance, and the obvious one is "a literal matches if some
  backend path starts with it".

  THAT RULE SILENTLY PASSES THE EXACT DEFECT IT EXISTS TO CATCH. Measured
  during the planning cycle, simulating the P0-2 state:

      naive prefix rule   : /api/data/upload -> []          (passes; WRONG)
      segment-aware rule  : /api/data/upload -> FLAGGED     (correct)

  `/api/data/upload` is a string prefix of `/api/data/uploads`, so the naive
  rule waves it through. The rule below matches a trailing-slash literal only
  where the NEXT PATH SEGMENT is a parameter (`{upload_id}`) - never on raw
  string prefix. Do not simplify it back.

WHAT THIS DOES NOT CATCH: renamed response fields and changed semantics. A
backend renaming `can_commit`, or returning `[]` where it used to return
`null`, still passes here. That gap is TD-009 (generated OpenAPI TypeScript
types) and is named rather than left to be rediscovered as an incident.
"""
import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.main import app  # noqa: E402

SRC = os.path.join(_ROOT, "frontend", "src")

# A quoted path literal in a .ts/.tsx file. Template expressions (`${...}`)
# terminate the match, which is what produces the trailing-slash prefixes the
# rule below has to handle.
PATH_LITERAL = re.compile(r"""['"`](/api/[a-z0-9/_-]*)""")

# `{upload_id}` immediately after the literal, optionally with more path after.
PARAMETER_SEGMENT = re.compile(r"\{[^/]+\}(/.*)?$")


@pytest.fixture(scope="module")
def backend_paths():
    return set(app.openapi()["paths"])


@pytest.fixture(scope="module")
def frontend_paths():
    found = {}
    for dirpath, dirnames, files in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", "assets"}]
        for name in sorted(files):
            if not name.endswith((".ts", ".tsx")):
                continue
            # Test files name paths that deliberately do not exist ('/api/x',
            # a 404 fixture). Scanning them would make the contract check fail
            # on its own fixtures.
            if name.endswith((".test.ts", ".test.tsx")):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                for match in PATH_LITERAL.finditer(handle.read()):
                    found.setdefault(match.group(1), set()).add(
                        os.path.relpath(path, SRC))
    return found


def matches(literal, backend_paths):
    """Segment-aware. See the module docstring for why not a prefix check."""
    if literal in backend_paths:
        return True
    if literal.endswith("/"):
        for served in backend_paths:
            if served.startswith(literal) and PARAMETER_SEGMENT.match(
                    served[len(literal):]):
                return True
    return False


def test_every_frontend_path_is_a_route_the_backend_serves(
        frontend_paths, backend_paths):
    unmatched = {p: sorted(files) for p, files in frontend_paths.items()
                 if not matches(p, backend_paths)}
    print("\n[contract] frontend literals: {} | backend routes: {}".format(
        len(frontend_paths), len(backend_paths)))
    assert not unmatched, (
        "the frontend calls paths the backend does not serve. This is the "
        "P0-2 failure shape: the route was deleted and the literal survived, "
        "so nothing failed until a client used the feature. {}".format(unmatched))


def test_the_rule_flags_a_simulated_p0_2(backend_paths):
    """The regression proof: with the route gone and the literal kept, the
    check fires."""
    assert "/api/data/upload" not in backend_paths, (
        "precondition: P0-2 removed this route")
    assert not matches("/api/data/upload", backend_paths)


def test_the_naive_prefix_rule_would_have_missed_it(backend_paths):
    """Pinned so nobody simplifies the rule back.

    `/api/data/upload` is a string prefix of `/api/data/uploads`, so a
    startswith-based template allowance passes the defect through.
    """
    naive = any(served.startswith("/api/data/upload")
                for served in backend_paths)
    assert naive, "a naive prefix rule would have considered this path served"
    assert not matches("/api/data/upload", backend_paths), (
        "the segment-aware rule must still flag it")


def test_template_literals_are_allowed_where_a_parameter_follows(backend_paths):
    """`/api/data/uploads/${id}` scans as `/api/data/uploads/` and is real."""
    assert matches("/api/data/uploads/", backend_paths)


def test_an_invented_path_is_flagged(backend_paths):
    assert not matches("/api/not-a-route", backend_paths)
    assert not matches("/api/data/uploads/nonsense", backend_paths)
