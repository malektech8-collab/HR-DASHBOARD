"""Structural guards on the frontend source.

These are Python tests scanning TypeScript, which is unusual and deliberate:
a source-wide scan sees every file at once, including files no component test
would import, which is what a "there is exactly one X in the codebase" rule
needs.

NOT because CI lacks a frontend runner. It has one - Gate 2 runs
`npx vitest run src/` - and an earlier version of this docstring claimed
otherwise, which was wrong and is corrected here so nobody cites it as grounds
to skip writing component tests. What vitest currently collects is 1 file and
3 tests, all of GovernanceWidget: the harness exists and is nearly empty, which
is why P0-2 broke the Data Quality upload widget invisibly.

What they hold:

  * one HTTP client. `api.ts` had 77 fetch sites and not one sent an
    Authorization header, while hooks/useGovernance.ts had a complete auth
    client of its own. P0-2 then authenticated six routes, which made every one
    of them unreachable from the frontend - a gap invisible precisely because
    the two halves lived in different files.
  * `uploadFile()` is gone (TD-005), and nothing still points at the removed
    endpoint.
"""
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(_ROOT, "frontend", "src")

# The one module allowed to call fetch(). `lib/http.ts` owns the token, the
# 401 handling and the base URL.
HTTP_MODULE = os.path.join("lib", "http.ts")


def _sources():
    for dirpath, dirnames, files in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", "assets"}]
        for name in sorted(files):
            if name.endswith((".ts", ".tsx")):
                path = os.path.join(dirpath, name)
                yield os.path.relpath(path, SRC), open(path, encoding="utf-8").read()


def test_only_one_module_calls_fetch():
    offenders = []
    for relative, text in _sources():
        if relative.replace("\\", "/") == HTTP_MODULE.replace("\\", "/"):
            continue
        if relative.endswith((".test.ts", ".test.tsx")):
            continue
        # strip line comments so prose about fetch does not trip the guard -
        # the P0-2 silver check failed on exactly that
        code = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith(("//", "*", "/*")))
        for match in re.finditer(r"(?<![\w.])fetch\s*\(", code):
            offenders.append("{}:{}".format(
                relative, code[:match.start()].count("\n") + 1))
    assert not offenders, (
        "every request must go through lib/http.ts, which attaches the auth "
        "token; a second client is how the frontend ended up unable to call "
        "its own authenticated routes: {}".format(offenders))


def test_upload_file_is_gone_and_nothing_points_at_the_removed_endpoint():
    """TD-005. It was dead before P0-2 and dead AND WRONG after."""
    offenders = []
    for relative, text in _sources():
        code = "\n".join(line for line in text.splitlines()
                         if not line.lstrip().startswith(("//", "*", "/*")))
        if re.search(r"\buploadFile\b", code):
            offenders.append("{}: uploadFile".format(relative))
        if re.search(r"['\"`]/api/data/upload['\"`]", code):
            offenders.append("{}: /api/data/upload".format(relative))
    assert not offenders, offenders


def test_the_staged_flow_uses_all_three_calls():
    """One call became three, and the middle one is the point. A page that
    staged and committed without previewing would be the old defect with extra
    steps."""
    page = open(os.path.join(SRC, "pages", "DataOnboarding.tsx"),
                encoding="utf-8").read()
    for call in ("stageUpload", "previewUpload", "commitUpload", "discardUpload"):
        assert call in page, call


def test_reject_and_exception_render_in_separate_regions():
    """They differ in what happens next, not in how bad they are, so they are
    never one list sorted by severity."""
    panels = open(os.path.join(SRC, "components", "widgets", "ViolationPanels.tsx"),
                  encoding="utf-8").read()
    assert 'data-testid="reject-panel"' in panels
    assert 'data-testid="exception-panel"' in panels
    assert "must be fixed before this can be committed" in panels
    assert "do not block the upload" in panels


def test_the_commit_button_is_gated_on_can_commit_and_the_declaration():
    page = open(os.path.join(SRC, "pages", "DataOnboarding.tsx"),
                encoding="utf-8").read()
    assert "disabled={!preview.can_commit || !declarationReady" in page
    # the label carries the consequence when only exceptions remain
    assert "will be recorded" in page
    # and the declaration needs an active confirmation, not just a pre-filled field
    assert "&& confirmed);" in page


def test_the_error_report_carries_the_true_total_and_a_truncation_line():
    """Ruling 5. The validator stops rendering at 100; a report that silently
    showed 100 rows would send the user round the fix-and-retry loop. Raising
    the cap is a validator change and is deliberately not done here."""
    uploads = open(os.path.join(SRC, "lib", "uploads.ts"), encoding="utf-8").read()
    assert "RENDERED_VIOLATION_CAP = 100" in uploads
    assert "there may be more" in uploads
    assert "buildErrorReport" in uploads


def test_the_onboarding_screen_reuses_the_dashboard_components():
    """Not parallel ones: the checklist should explain the dashboard's blanks
    in the dashboard's own words."""
    table = open(os.path.join(SRC, "components", "widgets",
                              "OnboardingStatusTable.tsx"), encoding="utf-8").read()
    assert "from '../ui/NotProvided'" in table
    assert "from '../ui/CoverageNote'" in table


def test_the_data_quality_page_no_longer_has_its_own_upload_widget():
    """It renamed the file client-side to force the target table - a workaround
    for the filename-derived table that P0-2 removed - and told the user the
    CSV would be 'routed directly to the Silver layer', which was the defect."""
    page = open(os.path.join(SRC, "pages", "DataQuality.tsx"), encoding="utf-8").read()
    assert "useUploadMutation" not in page
    assert "routed directly to the Silver layer" not in page
    assert "Go to Data Onboarding" in page
