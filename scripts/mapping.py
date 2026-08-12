"""Mapping profiles (upload-mapping cycle A).

A real HR export does not match the canonical schema: Arabic headers with
inconsistent spacing, client-specific status vocabularies, columns the contract
has no home for, and derived fields absent from the source. Rule 2 rejects it
on the first upload, correctly, and a mapping profile is the sanctioned way to
reconcile it — recorded once, reused on every subsequent upload.

FOUR PROPERTIES, each load-bearing.

1. ROW-PRESERVING, WITH A BACK-MAP. Applying a profile renames and derives; it
   never filters, reorders or deduplicates. Every violation therefore still
   addresses the client's own row, and `source_column` lets the UI name the
   client's own header. Without this, a client reads "Row 47, Joining Date"
   about a canonical column they never wrote in a file they never made.

2. UPLOAD-TIME ONLY. The mapped file is canonical, lands in data/raw, and is
   revalidated by scripts/ingest_raw.py unchanged. Nothing downstream knows
   profiles exist, so this mechanism cannot become a second ingest path.

3. NO EVAL, EVER. A profile names a derivation RULE resolved through
   derivations.REGISTRY. It never carries an expression. A profile is
   operator-supplied data; treating it as code would make it an execution
   vector, and `load_profile` refuses anything expression-shaped rather than
   trusting that nobody will try.

4. NO CLIENT PII IN THE EVIDENCE. Profiles accumulate as training substrate for
   the AI column mapper, so what goes in them outlives the upload. Verbatim
   sample values are kept ONLY for columns whose canonical target declares
   `allowed_values` — there the values are a vocabulary and are the signal.
   Everywhere else the evidence is a redacted shape: dtype, cardinality, length
   range, pattern. A name or a salary adds nothing a model can use that the
   header does not already carry.

   PRODUCT-ARCHITECTURE §4 originally said to record "sample values" without
   qualification. That is corrected in the same cycle as this module.
"""
import datetime
import hashlib
import os
import re

import yaml

import canonical_schema as _cs
import derivations as _der
from text import normalise

PROFILE_DIR = os.path.join("data", "mapping")
CONTAINER_PROFILE_DIR = "/app/data/mapping"

# A profile is data. Anything that looks like it wants to be executed is
# refused outright rather than being carefully sandboxed.
_EXPRESSION_SHAPED = re.compile(
    r"(lambda\b|__|\beval\b|\bexec\b|\bimport\b|\bopen\s*\(|\bos\.|\bsys\.)")

# How many distinct values are worth keeping for a vocabulary column. A status
# column has a handful; anything larger is not a vocabulary and the cap stops a
# high-cardinality column sneaking through the enum branch.
MAX_VOCABULARY_SAMPLES = 25


class MappingError(ValueError):
    """The profile is missing, malformed, or asks for something not allowed."""


def profile_dir():
    if os.path.isdir(os.path.dirname(CONTAINER_PROFILE_DIR)):
        return CONTAINER_PROFILE_DIR
    return PROFILE_DIR


def profile_path(table):
    return os.path.join(profile_dir(), "{}.yml".format(table))


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def _reject_expressions(node, where="profile"):
    """Walk the parsed YAML and refuse anything expression-shaped."""
    if isinstance(node, dict):
        for key, value in node.items():
            _reject_expressions(key, where)
            _reject_expressions(value, "{}.{}".format(where, key))
    elif isinstance(node, (list, tuple)):
        for item in node:
            _reject_expressions(item, where)
    elif isinstance(node, str):
        if _EXPRESSION_SHAPED.search(node):
            raise MappingError(
                "{}: value {!r} looks like an expression. A mapping profile is "
                "DATA. Derivations name a rule from the registry in "
                "scripts/derivations.py; they never carry code, because a "
                "profile is supplied by an operator and executing it would "
                "make a config file an execution vector.".format(where, node))


def load_profile(table, path=None, contracted=None):
    """The latest version of a table's profile, or None if there is none."""
    path = path or profile_path(table)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle) or {}
    _reject_expressions(spec, "profile[{}]".format(table))

    versions = spec.get("versions") or []
    if not versions:
        raise MappingError("{}: no versions recorded.".format(path))
    latest = max(versions, key=lambda v: int(v.get("version", 0)))
    _validate_targets(table, latest, contracted=contracted)
    return latest


def _validate_targets(table, version, contracted=None):
    """Every canonical target must exist on the contract. A typo that mapped to
    nothing would drop the column silently, which is the failure this whole
    mechanism exists to make impossible."""
    known = {c["name"] for c in _cs.columns(table)}
    unknown = sorted(set((version.get("columns") or {}).values()) - known)
    if unknown:
        raise MappingError(
            "profile for '{}' maps to unknown canonical column(s) {}. "
            "Contract columns are {}.".format(table, unknown, sorted(known)))
    for target in (version.get("derive") or {}):
        if target not in known:
            raise MappingError(
                "profile for '{}' derives unknown column '{}'.".format(table, target))
    for target in (version.get("values") or {}):
        if target not in known:
            raise MappingError(
                "profile for '{}' maps values for unknown column '{}'."
                .format(table, target))
    for target, rule in (version.get("derive") or {}).items():
        # resolve() raises on anything not in the registry - no eval, and a new
        # rule is reviewed code rather than config
        _der.resolve(rule["rule"] if isinstance(rule, dict) else rule)
    return True


def header_fingerprint(headers):
    """Detects a changed export, so a stale profile is questioned rather than
    silently applied to a file it was not written for."""
    joined = "".join(sorted(str(h) for h in headers))
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# the PII rule
# --------------------------------------------------------------------------

def is_vocabulary_column(table, canonical):
    """True when the canonical target declares allowed_values.

    This is the whole PII rule in one predicate: a vocabulary's values ARE the
    training signal and are not personal data; a name's or a salary's are the
    opposite on both counts.
    """
    if not canonical:
        return False
    for column in _cs.columns(table):
        if column["name"] == canonical:
            return bool(column.get("allowed_values"))
    return False


def _pattern_of(values):
    """A coarse shape, not the value: digits -> 9, letters -> A."""
    if not values:
        return None
    shape = re.sub(r"\d", "9", re.sub(r"[^\W\d_]", "A", str(values[0]),
                                      flags=re.UNICODE))
    return shape[:32]


def value_profile(table, canonical, values):
    """Evidence for one source column, redacted unless it is a vocabulary.

    Returns a dict that is safe to persist. Nothing here may contain a
    client's personal data unless `is_vocabulary_column` is true.
    """
    present = [v for v in values if v not in (None, "")]
    if is_vocabulary_column(table, canonical):
        distinct = sorted({str(v) for v in present})
        return {
            "kind": "vocabulary",
            "distinct_values": distinct[:MAX_VOCABULARY_SAMPLES],
            "cardinality": len(distinct),
            "truncated": len(distinct) > MAX_VOCABULARY_SAMPLES,
        }
    lengths = [len(str(v)) for v in present]
    return {
        "kind": "redacted",
        "dtype": "empty" if not present else (
            "number" if all(_looks_numeric(v) for v in present) else "string"),
        "cardinality": len({str(v) for v in present}),
        "length_range": [min(lengths), max(lengths)] if lengths else None,
        "pattern": _pattern_of(present),
    }


def _looks_numeric(value):
    try:
        float(str(value).replace(",", ""))
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------
# applying a profile
# --------------------------------------------------------------------------

class MappingReport(object):
    """What applying a profile did, and what still needs a human."""

    def __init__(self):
        self.renamed = {}            # source header -> canonical
        self.ignored = []            # source headers dropped, by declaration
        self.unmapped = []           # source headers with no decision - BLOCKS
        self.derived = []            # canonical columns produced by a rule
        self.value_mapped = {}       # canonical -> {source value: canonical}
        self.unmapped_values = {}    # canonical -> [values with no mapping]
        self.row_count = 0

    @property
    def back_map(self):
        """canonical column -> the client's own header. Violations use this so
        a client is never shown a column name they did not write."""
        return {canonical: source for source, canonical in self.renamed.items()}

    def as_dict(self):
        return {
            "renamed": dict(self.renamed),
            "ignored": list(self.ignored),
            "unmapped": list(self.unmapped),
            "derived": list(self.derived),
            "unmapped_values": {k: sorted(v) for k, v in self.unmapped_values.items()},
            "row_count": self.row_count,
            "back_map": self.back_map,
        }


def apply_profile(frame, table, version):
    """Rename, map values and derive. Returns (mapped_frame, MappingReport).

    ROW-PRESERVING by construction: this function only ever renames columns,
    replaces cell values within a column, and appends derived columns. There is
    no filter, no sort and no dedupe anywhere in it, and a test asserts the row
    count and row identity survive.
    """
    import polars as pl

    report = MappingReport()
    report.row_count = frame.height

    columns = (version.get("columns") or {})
    ignored = {entry["header"] if isinstance(entry, dict) else entry
               for entry in (version.get("ignored") or [])}

    # normalised lookup so a trailing space or an alef variant in the header
    # does not defeat a mapping the operator already made
    by_normalised = {normalise(source): (source, canonical)
                     for source, canonical in columns.items()}
    ignored_normalised = {normalise(h) for h in ignored}

    rename = {}
    drop = []
    for header in frame.columns:
        key = normalise(header)
        if key in by_normalised:
            _source, canonical = by_normalised[key]
            rename[header] = canonical
            report.renamed[header] = canonical
        elif key in ignored_normalised:
            drop.append(header)
            report.ignored.append(header)
        else:
            report.unmapped.append(header)

    mapped = frame.drop(drop).rename(rename)

    # value vocabularies, compared after normalisation so "نشط " and "نشط"
    # need one entry rather than two
    for canonical, pairs in (version.get("values") or {}).items():
        if canonical not in mapped.columns:
            continue
        lookup = {normalise(k): v for k, v in pairs.items()}
        report.value_mapped[canonical] = dict(pairs)
        column = mapped[canonical].to_list()
        translated, unmapped = [], set()
        allowed = _allowed_values(table, canonical)
        for value in column:
            if value in (None, ""):
                translated.append(value)
                continue
            key = normalise(value)
            if key in lookup:
                translated.append(lookup[key])
            else:
                translated.append(value)
                if allowed and str(value) not in allowed:
                    unmapped.add(str(value))
        mapped = mapped.with_columns(pl.Series(canonical, translated))
        if unmapped:
            report.unmapped_values[canonical] = unmapped

    # derivations: the profile names a rule and a SOURCE header; the rule is
    # resolved from the registry, never evaluated
    for canonical, spec in (version.get("derive") or {}).items():
        rule = spec["rule"] if isinstance(spec, dict) else spec
        source = spec.get("from") if isinstance(spec, dict) else None
        if canonical in mapped.columns:
            continue
        if source is None or source not in frame.columns:
            raise MappingError(
                "derive.{}: source column {!r} is not in the uploaded file."
                .format(canonical, source))
        produced = _der.resolve(rule)(frame[source].to_list())
        mapped = mapped.with_columns(pl.Series(canonical, produced))
        report.derived.append(canonical)

    assert mapped.height == report.row_count, "apply_profile must preserve rows"
    return mapped, report


def _allowed_values(table, canonical):
    for column in _cs.columns(table):
        if column["name"] == canonical:
            return set(column.get("allowed_values") or [])
    return set()


def reject_enum_columns(table):
    """Canonical columns where an unmapped value BLOCKS the upload.

    Three today. The distinction matters to the UI: for these, an unmapped
    value is a mapping task with the canonical options listed - never a bare
    rejection that sends a client back to Excel to rename a word the product
    could learn once.
    """
    out = {}
    for column in _cs.columns(table):
        allowed = column.get("allowed_values")
        if not allowed:
            continue
        if str(column.get("on_violation", "")).lower() != "exception":
            out[column["name"]] = list(allowed)
    return out


# --------------------------------------------------------------------------
# writing a profile
# --------------------------------------------------------------------------

def save_version(table, version, path=None, contracted=None):
    """Append a version. Never mutate one.

    A client's export changes. If a profile mutated, nobody could say which
    mapping produced last month's numbers, and the accumulated evidence - the
    substrate the AI mapper learns from - would lose exactly the history that
    makes it valuable.
    """
    path = path or profile_path(table)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    spec = {"table": table, "versions": []}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            spec = yaml.safe_load(handle) or spec
    _reject_expressions(version, "new version")
    _validate_targets(table, version, contracted=contracted)

    existing = spec.get("versions") or []
    version = dict(version)
    version["version"] = max([int(v.get("version", 0)) for v in existing] or [0]) + 1
    version.setdefault("created_at",
                       datetime.datetime.now().isoformat(timespec="seconds"))
    assert_no_pii(table, version)
    existing.append(version)
    spec["versions"] = existing
    spec["table"] = table
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(spec, handle, allow_unicode=True, sort_keys=False)
    return version


def assert_no_pii(table, version):
    """The PII rule, enforced at the write.

    A comment saying "do not put values here" is not a control. This refuses to
    persist verbatim values for any column whose canonical target does not
    declare allowed_values.
    """
    offenders = []
    for entry in (version.get("evidence") or []):
        profile = entry.get("value_profile") or {}
        canonical = entry.get("chosen")
        if profile.get("kind") == "vocabulary" and not is_vocabulary_column(
                table, canonical):
            offenders.append(entry.get("source_header"))
        if profile.get("kind") != "vocabulary" and "distinct_values" in profile:
            offenders.append(entry.get("source_header"))
    if offenders:
        raise MappingError(
            "refusing to store verbatim sample values for column(s) {} in the "
            "'{}' profile. Profiles accumulate as training substrate, so their "
            "contents outlive the upload; verbatim values are kept only where "
            "the canonical target declares allowed_values, because there they "
            "are a vocabulary rather than a person.".format(offenders, table))
    return True


def build_evidence(table, frame, version):
    """Evidence for every source header, with the PII rule already applied.

    Records the verbatim header, what it normalised to, what it was matched to
    and - the part that cannot be reconstructed later - the candidates a human
    REJECTED.
    """
    columns = version.get("columns") or {}
    ignored = {entry["header"] if isinstance(entry, dict) else entry
               for entry in (version.get("ignored") or [])}
    prior = {e.get("source_header"): e for e in (version.get("evidence") or [])}

    evidence = []
    for header in frame.columns:
        chosen = columns.get(header)
        existing = prior.get(header, {})
        evidence.append({
            "source_header": header,
            "normalised": normalise(header),
            "matched_by": existing.get("matched_by", "human"),
            "confidence": existing.get("confidence"),
            "chosen": chosen,
            # An explicit decision rather than a sentinel value. The first
            # version used "__ignored__", which tripped this module's own
            # no-expression guard on the dunder - a small illustration that a
            # magic string is not a data model.
            "decision": ("mapped" if chosen else
                         ("ignored" if header in ignored else "undecided")),
            "rejected": existing.get("rejected", []),
            "value_profile": value_profile(table, chosen,
                                           frame[header].to_list()),
        })
    return evidence
