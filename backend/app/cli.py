# -*- coding: utf-8 -*-
"""Operator CLI for accounts.

FIRST-RUN BOOTSTRAP - the question the dict literal was avoiding.

    A fresh deployment must reach a working admin account without a credential
    ever existing in a file, an image, an environment variable or the
    repository. `MOCK_USER_DB` "answered" it by shipping three passwords in
    source, which is the one option that fails that requirement completely.

    This is the answer for a client-hosted deployment, where an operator has a
    shell on the box:

        python -m app.cli create-admin --email operator@client.example

    The password is PROMPTED via getpass - never in argv, so never in shell
    history and never visible in `ps`. Nothing is written anywhere except the
    argon2 hash.

    For vendor-hosted, where there may be no interactive shell, the backend
    prints a single-use bootstrap token to the container log on a zero-user
    deployment; see app/api/endpoints/bootstrap.py.

Usage:
    python -m app.cli create-admin --email you@example.com
    python -m app.cli create-user  --email hr@example.com --role HR_ANALYST
    python -m app.cli set-password  --email you@example.com
    python -m app.cli list-users
    python -m app.cli deactivate    --email old@example.com
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import users  # noqa: E402
from app.core.security import Role  # noqa: E402


def _prompt_password() -> str:
    first = getpass.getpass("Password (min 12 chars): ")
    second = getpass.getpass("Repeat: ")
    if first != second:
        raise SystemExit("Passwords do not match. Nothing was created.")
    return first


def cmd_create_admin(args):
    return _create(args.email, Role.SYSTEM_ADMIN)


def cmd_create_user(args):
    try:
        role = Role(args.role)
    except ValueError:
        raise SystemExit("Unknown role {!r}. One of: {}".format(
            args.role, ", ".join(r.value for r in Role)))
    return _create(args.email, role)


def _create(email, role):
    users.initialise()
    try:
        user = users.create(email, _prompt_password(), role)
    except users.UserStoreError as exc:
        raise SystemExit(str(exc))
    print("Created {} as {}.".format(user["email"], role.value))
    print("Store: {}".format(users.store_path()))
    return 0


def cmd_set_password(args):
    try:
        users.set_password(args.email, _prompt_password())
    except users.UserStoreError as exc:
        raise SystemExit(str(exc))
    print("Password updated for {}.".format(args.email))
    print("Existing tokens remain valid until they expire.")
    return 0


def cmd_list_users(args):
    rows = users.listing()
    if not rows:
        print("No users. This deployment has not been initialised.")
        return 0
    for user in rows:
        print("  {:<34} {:<14} {}".format(
            user["email"], user["role"].value,
            "active" if user["is_active"] else "INACTIVE"))
    return 0


def cmd_deactivate(args):
    users.deactivate(args.email)
    print("{} deactivated. This takes effect on their NEXT REQUEST, because "
          "the role is read per request rather than carried in the token."
          .format(args.email))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="app.cli", description="Account management for this deployment.")
    subs = parser.add_subparsers(dest="command")

    p = subs.add_parser("create-admin", help="create the first administrator")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_create_admin)

    p = subs.add_parser("create-user")
    p.add_argument("--email", required=True)
    p.add_argument("--role", required=True,
                   help=", ".join(r.value for r in Role))
    p.set_defaults(func=cmd_create_user)

    p = subs.add_parser("set-password")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_set_password)

    p = subs.add_parser("list-users")
    p.set_defaults(func=cmd_list_users)

    p = subs.add_parser("deactivate")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_deactivate)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
