"""Canonical bilingual schema loader (Phase 1a).

One definition, four consumers: the downloadable template, the validation
rules, the UI labels, and the error messages. This module is the single way to
read data/contracts/*_schema.yml; nothing else should parse those files.

Placement (Phase 1a): kept in scripts/ deliberately. A shared module at the
repository root would not be visible to the backend image, whose Docker build
context is ./backend — the backend only sees data/ and scripts/ via the
compose bind-mounts. Promoting this to a top-level `hr_schema/` package, with
the definitions alongside it and the build context widened, is cycle 1b.

Dependencies: PyYAML only. Importable from scripts/ and from backend/ without
dragging in the API.

This module is READ-ONLY with respect to validation: it does not validate
anything and does not change validator behaviour. scripts/validate_schema.py
remains the enforcement point and continues to read the YAML itself.
"""
import os
import threading

import yaml

# data/contracts relative to the repository root, plus the container path the
# backend sees when docker-compose bind-mounts ./data to /app/data.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
DEFAULT_CONTRACTS_DIR = os.path.join(_REPO_ROOT, "data", "contracts")
CONTAINER_CONTRACTS_DIR = "/app/data/contracts"

LOCALES = ("en", "ar")
DEFAULT_LOCALE = "en"

_cache = {}
_cache_lock = threading.Lock()


class SchemaNotFoundError(FileNotFoundError):
    """Raised when a table has no contract."""


def contracts_dir():
    """Resolve the contracts directory for the current environment."""
    if os.path.isdir(CONTAINER_CONTRACTS_DIR):
        return CONTAINER_CONTRACTS_DIR
    return DEFAULT_CONTRACTS_DIR


def _contract_path(table, directory=None):
    return os.path.join(directory or contracts_dir(), "{}_schema.yml".format(table))


def available_tables(directory=None):
    """Sorted list of tables that have a contract."""
    d = directory or contracts_dir()
    if not os.path.isdir(d):
        return []
    return sorted(
        f[: -len("_schema.yml")]
        for f in os.listdir(d)
        if f.endswith("_schema.yml")
    )


def has_schema(table, directory=None):
    return os.path.exists(_contract_path(table, directory))


def load_schema(table, directory=None):
    """Full parsed contract for one table. Cached by path and mtime."""
    path = _contract_path(table, directory)
    if not os.path.exists(path):
        raise SchemaNotFoundError(
            "No contract at {}. A template, label set, or validation rule "
            "cannot be produced for '{}' without one.".format(path, table)
        )
    key = (path, os.path.getmtime(path))
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    if not spec.get("columns"):
        raise SchemaNotFoundError("Contract {} defines no columns.".format(path))
    with _cache_lock:
        _cache[key] = spec
    return spec


def columns(table, directory=None):
    """Column definitions, in contract order."""
    return load_schema(table, directory)["columns"]


def column_names(table, directory=None):
    """Canonical column names, in contract order.

    This is the ordering used for template headers and for any consumer that
    needs the column list; nothing should hardcode it.
    """
    return [c["name"] for c in columns(table, directory)]


def required_columns(table, directory=None):
    return [c["name"] for c in columns(table, directory) if c.get("required")]


def _localised(spec, base, locale, fallback):
    """Pick `<base>_<locale>`, falling back to English then to `fallback`."""
    if locale not in LOCALES:
        locale = DEFAULT_LOCALE
    return (
        spec.get("{}_{}".format(base, locale))
        or spec.get("{}_{}".format(base, DEFAULT_LOCALE))
        or fallback
    )


def column_label(table, column, locale=DEFAULT_LOCALE, directory=None):
    """Display label for one column. Falls back to the canonical name."""
    for c in columns(table, directory):
        if c["name"] == column:
            return _localised(c, "name", locale, column)
    return column


def column_labels(table, locale=DEFAULT_LOCALE, directory=None):
    """{canonical_name: label} for every column."""
    return {
        c["name"]: _localised(c, "name", locale, c["name"])
        for c in columns(table, directory)
    }


def table_label(table, locale=DEFAULT_LOCALE, directory=None):
    return _localised(load_schema(table, directory), "label", locale, table)


def value_label(table, column, value, locale=DEFAULT_LOCALE, directory=None):
    """Display label for an enum value, falling back to the raw value."""
    for c in columns(table, directory):
        if c["name"] == column:
            labels = (c.get("value_labels") or {}).get(value)
            if isinstance(labels, dict):
                return labels.get(locale) or labels.get(DEFAULT_LOCALE) or value
            return value
    return value


def describe(table, locale=DEFAULT_LOCALE, directory=None):
    """Localised, UI-ready view of a table's schema.

    Serialisable as-is. This is what the API exposes to the frontend, and it
    carries labels and metadata only — never data.
    """
    spec = load_schema(table, directory)
    out_cols = []
    for c in spec["columns"]:
        entry = {
            "name": c["name"],
            "label": _localised(c, "name", locale, c["name"]),
            "type": c.get("type", "VARCHAR"),
            "required": bool(c.get("required")),
            "description": _localised(c, "description", locale, ""),
            "example": c.get("example"),
        }
        if c.get("allowed_values"):
            entry["allowed_values"] = c["allowed_values"]
            entry["value_labels"] = {
                v: value_label(table, c["name"], v, locale, directory)
                for v in c["allowed_values"]
            }
        out_cols.append(entry)
    return {
        "table": spec.get("table", table),
        "version": spec.get("version"),
        "label": _localised(spec, "label", locale, table),
        "description": _localised(spec, "description", locale, ""),
        "locale": locale if locale in LOCALES else DEFAULT_LOCALE,
        "columns": out_cols,
    }


def describe_all(locale=DEFAULT_LOCALE, directory=None):
    return [describe(t, locale, directory) for t in available_tables(directory)]
