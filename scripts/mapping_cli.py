# -*- coding: utf-8 -*-
"""Author a mapping profile from a terminal. No browser required.

WHY THIS EXISTS, and why it is not optional.

  Cycle B makes `build_version` the only sanctioned way to produce a profile
  version, so evidence is captured by construction rather than by remembering.
  That deliberately breaks the cycle-A path where an operator hand-wrote YAML
  in a text editor - which is, today, the ONLY way a profile gets written at
  all. If the browser flow were the only replacement, a slip in that work would
  leave no way to write a profile and would regress the one capability Phase 2
  currently has.

  So the operator contract changes shape rather than vanishing: it stops being
  "write the whole profile by hand" and becomes "state your decisions, and the
  tool records how you reached them".

TWO STEPS.

  1. suggest - reads the client's CSV, runs the header ladder, and writes a
     decisions file with the machine's proposals filled in and every genuinely
     undecided column left blank for you.

  2. save - reads your edited decisions file, builds the version (evidence,
     matched_by, confidence, rejected candidates, fingerprint) and appends it.

THE AFFIRMATION IS NEVER PRE-FILLED. `suggest` writes the consequence of each
REJECT-enum value mapping into the decisions file as a comment and leaves the
`confirmations` block empty. Restating the pairs there is the affirmation - the
same act as ticking the box on the screen, and for the same reason: a mapping
that turns a client's word into a canonical one is silent once applied, so the
only trace it ever gets is the one a human leaves deliberately.

Usage:
    python scripts/mapping_cli.py suggest --table employees \\
        --file data/staging/<id>/data.csv --out decisions.yml

    python scripts/mapping_cli.py save --table employees \\
        --file data/staging/<id>/data.csv --decisions decisions.yml \\
        --by operator@client.example

    python scripts/mapping_cli.py show --table employees
"""
import argparse
import datetime
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402

import mapping  # noqa: E402

NEWLINE = chr(10)


def _key(header):
    """A source header as a safe YAML key.

    yaml.safe_dump of a bare scalar emits a whole document (trailing newline
    and `...`), which is not a key. A double-quoted scalar is valid YAML and
    JSON escapes it correctly, including the Arabic left untouched by
    ensure_ascii=False.
    """
    return json.dumps(header, ensure_ascii=False)


def _read(path):
    import polars as pl
    if not os.path.exists(path):
        raise SystemExit("no such file: {}".format(path))
    return pl.read_csv(path, null_values=[""])


def _consequence_block(table, columns):
    """The consequence text, as comments, above an EMPTY confirmations block."""
    lines = []
    for column in sorted(columns):
        note = mapping.consequence(table, column)
        if note:
            lines.append("#   {}: {}".format(column, note))
    return lines


def cmd_suggest(args):
    frame = _read(args.file)
    headers = list(frame.columns)
    ranked = mapping.suggest(args.table, headers)
    gated = mapping.reject_enum_columns(args.table)

    columns, undecided = {}, []
    for header in headers:
        best = (ranked.get(header) or [None])[0]
        # Rung 4 (alias) is a curated guess, so it is reported but NOT filled
        # in. Rungs 1-3 come from the contract itself and are.
        if best and best["matched_by"] != "alias":
            columns[header] = best["canonical"]
        else:
            undecided.append(header)

    out = [
        "# Mapping decisions for '{}', generated from {}.".format(
            args.table, os.path.basename(args.file)),
        "# {} of {} columns proposed from the contract; {} need you.".format(
            len(columns), len(headers), len(undecided)),
        "#",
        "# Every source header needs a decision. Map it under `columns`, or",
        "# list it under `ignored` with a reason. An undecided header BLOCKS",
        "# the upload - a column is never dropped by default, because a",
        "# renamed export would then lose one silently.",
        "",
        "columns:",
    ]
    for header, canonical in columns.items():
        best = ranked[header][0]
        out.append("  {}: {}   # {} ({})".format(
            _key(header), canonical, best["matched_by"], best["confidence"]))
    for header in undecided:
        alias = next((c for c in (ranked.get(header) or [])
                      if c["matched_by"] == "alias"), None)
        hint = ("  # SUGGESTION (alias, {}): {} - confirm or replace".format(
            alias["confidence"], alias["canonical"]) if alias
            else "  # no suggestion; map it or move it to `ignored`")
        out.append("  # {}:{}".format(_key(header), hint))

    out += [
        "",
        "ignored:",
        "  # - header: \"<source header>\"",
        "  #   reason: \"why this column has no canonical home\"",
        "",
        "values:",
        "  # <canonical column>:",
        "  #   \"<client's word>\": <canonical value>",
        "",
        "derive:",
        "  # is_saudi: {rule: nationality_is_saudi, from: \"<source header>\"}",
        "",
        "# ---------------------------------------------------------------",
        "# AFFIRMATION - deliberately empty. Nothing here is pre-filled.",
        "#",
        "# A value mapping into one of these columns is REJECTED unless the",
        "# same pairs are restated below with your name on them. Restating",
        "# them is the affirmation; it is duplication on purpose.",
    ]
    out += _consequence_block(args.table, gated)
    out += [
        "#",
        "# confirmations:",
        "#   status:",
        "#     pairs: {\"<client's word>\": <canonical value>}",
        "confirmations: {}",
        "",
    ]

    text = NEWLINE.join(out)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print("wrote {}".format(args.out))
        print("  {} proposed, {} need a decision: {}".format(
            len(columns), len(undecided), undecided))
        if gated:
            print("  affirmation required for: {}".format(sorted(gated)))
    else:
        print(text)
    return 0


def cmd_save(args):
    frame = _read(args.file)
    with io.open(args.decisions, encoding="utf-8") as handle:
        spec = yaml.safe_load(handle) or {}

    decisions = {}
    for header, canonical in (spec.get("columns") or {}).items():
        decisions[header] = {"decision": "mapped", "chosen": canonical}
    for entry in (spec.get("ignored") or []):
        header = entry["header"] if isinstance(entry, dict) else entry
        decisions[header] = {
            "decision": "ignored",
            "reason": entry.get("reason") if isinstance(entry, dict) else None}

    # The operator's restated pairs become the affirmation; the CLI supplies
    # only the attribution. It never invents a pair, so a mapping the operator
    # did not restate stays unaffirmed and the save is refused.
    confirmations = {}
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    for column, record in (spec.get("confirmations") or {}).items():
        pairs = (record or {}).get("pairs") or {}
        confirmations[column] = {"confirmed_by": args.by,
                                 "confirmed_at": stamp,
                                 "pairs": dict(pairs)}
        note = mapping.consequence(args.table, column)
        if note:
            print("affirming {}: {}".format(column, note))
            for source, target in sorted(pairs.items()):
                print("   {!r} -> {!r}".format(source, target))

    version = mapping.build_version(
        args.table, frame, decisions, created_by=args.by,
        values=spec.get("values"), derive=spec.get("derive"),
        confirmations=confirmations)

    undecided = [e["source_header"] for e in version["evidence"]
                 if e["decision"] == "undecided"]
    if undecided:
        print("WARNING: {} column(s) still undecided; the upload will block "
              "until they are mapped or ignored: {}".format(
                  len(undecided), undecided))

    if args.dry_run:
        print(yaml.safe_dump(version, allow_unicode=True, sort_keys=False))
        print("dry run: nothing written.")
        return 0

    saved = mapping.save_version(args.table, version, path=args.path)
    print("saved version {} of {} to {}".format(
        saved["version"], args.table, args.path or mapping.profile_path(args.table)))
    print("  {} mapped, {} ignored, {} undecided, {} derived".format(
        len(saved.get("columns") or {}), len(saved.get("ignored") or []),
        len(undecided), len(saved.get("derive") or {})))
    print("  attributed to {}".format(saved["created_by"]))
    return 0


def cmd_show(args):
    version = mapping.load_profile(args.table, path=args.path)
    if not version:
        print("no profile for '{}'.".format(args.table))
        return 0
    print("{} profile, version {} by {} at {}".format(
        args.table, version.get("version"), version.get("created_by"),
        version.get("created_at")))
    print("  {} mapped, {} ignored, {} value vocabularies, {} derived".format(
        len(version.get("columns") or {}), len(version.get("ignored") or []),
        len(version.get("values") or {}), len(version.get("derive") or {})))
    for column, record in (version.get("confirmations") or {}).items():
        print("  affirmed {} by {} at {}: {}".format(
            column, record.get("confirmed_by"), record.get("confirmed_at"),
            record.get("pairs")))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mapping_cli",
        description="Author a mapping profile without a browser.")
    subs = parser.add_subparsers(dest="command")

    p = subs.add_parser("suggest", help="propose decisions from a client CSV")
    p.add_argument("--table", required=True)
    p.add_argument("--file", required=True, help="the client's CSV")
    p.add_argument("--out", help="write the decisions file here")
    p.set_defaults(func=cmd_suggest)

    p = subs.add_parser("save", help="build and append a version")
    p.add_argument("--table", required=True)
    p.add_argument("--file", required=True, help="the client's CSV")
    p.add_argument("--decisions", required=True)
    p.add_argument("--by", required=True,
                   help="who is asserting this mapping; recorded on the version")
    p.add_argument("--path", help="profile file (defaults to data/mapping/)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_save)

    p = subs.add_parser("show", help="summarise the current profile")
    p.add_argument("--table", required=True)
    p.add_argument("--path")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except mapping.MappingError as exc:
        print("REFUSED: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
