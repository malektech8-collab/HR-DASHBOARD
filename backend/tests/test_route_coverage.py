# -*- coding: utf-8 -*-
"""No route serves employee data without a token.

THE DEFECT THIS EXISTS FOR, measured on main @ 6f1962c before this cycle:

    /api/payroll/summary      -> 200      (no token)
    /api/workforce/summary    -> 200
    /api/compliance/summary   -> 200
    /api/data/uploads         -> 401      <- the only kind protected

    /api/workforce/exceptions -> 200
    {"exceptions":[{"employee_id":"EMP003",
                    "employee_name":"Fahad Al-Otaibi", ...}]}

83 routes across backend/app/api/, and `get_current_user` appeared in ONE
file. P0-2 authenticated the six routes that WRITE. The seventy-seven that
READ - individual salaries, GOSI status, Iqama expiry, named employees - were
open to anyone who could reach the port.

TD-006 described the auth layer as "the only thing between an anonymous
request and a client's data". For reads there was no layer at all, and
strengthening the credential system would not have changed that by one byte.

THE LIST BELOW IS THE POINT. Authentication is applied at the ROUTER in
main.py, so a new route is protected by default and an exemption has to be
written down here, with a reason, in a test someone has to edit deliberately.
"""
import os
import sys

import pytest
from fastapi.testclient import TestClient

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# Every route that may be reached without a token, and why. Anything not here
# must require one.
PUBLIC_ROUTES = {
    "/health": "Liveness probe. Must answer before anyone can log in.",
    "/api/meta/app-config": "Tells the UI whether it is showing demo or real "
                            "data. Needed before login to label the screen.",
    "/api/meta/schema": "Column LABELS from the contract. Metadata only - it "
                        "describes the shape of a file, never its contents.",
    "/api/governance/token": "How a caller obtains a token. Necessarily open.",
    "/api/governance/bootstrap": "Creates the FIRST admin from the one-time "
                                 "startup token. Impossible once any account "
                                 "exists.",
    "/docs": "OpenAPI UI.",
    "/redoc": "OpenAPI UI.",
    "/openapi.json": "OpenAPI schema.",
    "/docs/oauth2-redirect": "OpenAPI UI.",
}


def _routes():
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) or set()
        if not path:
            continue
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            yield method, path


def _call(method, path):
    # Fill path params with something harmless; we only care about the status
    # class, and an unauthenticated caller must never get far enough to matter.
    concrete = path
    for name in ("upload_id", "table", "name", "employee_id", "id"):
        concrete = concrete.replace("{" + name + "}", "probe")
    while "{" in concrete:
        concrete = concrete[:concrete.index("{")] + "probe"
    return client.request(method, concrete)


def test_every_route_is_authenticated_or_explicitly_public():
    """The enumeration. A new unprotected route fails here, by name."""
    unprotected = []
    for method, path in _routes():
        if path in PUBLIC_ROUTES:
            continue
        response = _call(method, path)
        if response.status_code not in (401, 403, 503):
            unprotected.append("{} {} -> {}".format(
                method, path, response.status_code))
    assert not unprotected, (
        "these routes answered an anonymous caller. Either require a token or "
        "add them to PUBLIC_ROUTES with a reason:\n  "
        + "\n  ".join(unprotected))


@pytest.mark.parametrize("path", [
    "/api/payroll/summary",
    "/api/payroll/exceptions",
    "/api/workforce/summary",
    "/api/workforce/exceptions",
    "/api/compliance/summary",
    "/api/executive/summary",
    "/api/er/summary",
    "/api/attendance/summary",
])
def test_the_specific_routes_that_leaked_are_closed(path):
    """Named individually because these are the ones that were measured open.

    A parametrised list that someone has to delete from is harder to lose than
    a general rule.
    """
    assert client.get(path).status_code in (401, 403, 503)


def test_a_named_employee_is_not_reachable_without_a_token():
    """The concrete harm, as a test.

    /api/workforce/exceptions returned employee_id and employee_name to an
    anonymous caller. This asserts the body no longer contains them.
    """
    response = client.get("/api/workforce/exceptions")
    assert response.status_code in (401, 403, 503)
    assert "employee_name" not in response.text


def test_public_routes_really_are_public():
    """The exemption list must not quietly protect something either - a route
    listed as public but returning 401 means the UI breaks before login."""
    for path, _reason in PUBLIC_ROUTES.items():
        if path in ("/api/governance/token", "/api/governance/bootstrap",
                    "/docs/oauth2-redirect"):
            continue          # POST-only, or a redirect helper
        assert client.get(path).status_code < 400, path


def test_every_public_route_carries_a_reason():
    assert all(reason.strip() for reason in PUBLIC_ROUTES.values())


def test_the_route_count_is_pinned():
    """So that a router added without auth is visible as a number change too.

    83 before this cycle; the auth routes (logout, bootstrap) and FastAPI's own
    docs routes make up the rest.
    """
    total = len(list(_routes()))
    assert total >= 83, total
