"""Contract-based schema validation for real-data ingestion (Phase 0).

Hard gate applied ONLY to files taken from data/raw/ under data_mode='real'.
Validates a real CSV against its data/contracts/{table}_schema.yml before the
file is allowed into bronze/silver. On ANY violation it raises
SchemaValidationError with a specific message (file, column, rule) and writes
nothing — no partial load, no auto-coercion, no column-mapping guesses.

Rules enforced:
  1. Required columns present        (contract `required: true`)
  2. No unexpected columns           (any column not in the contract -> reject)
  3. Type conformance                (each value parses as the declared type)
  4. allowed_values                  (where the contract lists them)

Not used on the data/sample/ path, so demo/CI never invokes it.
"""
import os
import polars as pl
import yaml


class SchemaValidationError(ValueError):
    """Raised when a real CSV does not conform to its contract."""


# Declared contract type -> a polars parse expression producing null on failure.
# VARCHAR is never type-checked (any string is valid).
def _parse_expr(col: str, ctype: str):
    t = ctype.upper()
    if t == "INTEGER":
        return pl.col(col).cast(pl.Int64, strict=False)
    if t == "DECIMAL":
        return pl.col(col).cast(pl.Float64, strict=False)
    if t == "DATE":
        return pl.col(col).str.to_date("%Y-%m-%d", strict=False)
    if t == "TIMESTAMP":
        return pl.col(col).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
    if t == "BOOLEAN":
        # Accept true/false (any case); everything else is a violation.
        return (
            pl.when(pl.col(col).str.to_lowercase().is_in(["true", "false"]))
            .then(pl.col(col))
            .otherwise(None)
        )
    return None  # VARCHAR / unknown -> no parse check


def _load_contract(table: str, contracts_dir: str) -> list:
    path = os.path.join(contracts_dir, f"{table}_schema.yml")
    if not os.path.exists(path):
        raise SchemaValidationError(
            f"[{table}] no contract at {path}; a real CSV cannot be ingested "
            f"without a contract."
        )
    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f) or {}
    cols = spec.get("columns")
    if not cols:
        raise SchemaValidationError(f"[{table}] contract {path} has no 'columns'.")
    return cols


def validate_csv_against_contract(csv_path: str, table: str,
                                  contracts_dir: str = "data/contracts") -> None:
    """Validate csv_path against data/contracts/{table}_schema.yml.

    Returns None on success; raises SchemaValidationError on the first failure.
    """
    columns = _load_contract(table, contracts_dir)
    contract_names = [c["name"] for c in columns]
    contract_set = set(contract_names)
    required = [c["name"] for c in columns if c.get("required")]

    # Read every column as raw text so we can check parseability ourselves.
    # null_values=[""] treats empty cells as null (not as parse failures).
    df = pl.read_csv(csv_path, infer_schema_length=0, null_values=[""])
    actual = list(df.columns)
    actual_set = set(actual)

    # Rule 1: required columns present
    missing = [c for c in required if c not in actual_set]
    if missing:
        raise SchemaValidationError(
            f"[{table}] {csv_path}: missing required column(s) {missing}. "
            f"Rule: required-columns. Expected columns: {contract_names}."
        )

    # Rule 2: no unexpected columns (hard-reject per Decision-3)
    unexpected = [c for c in actual if c not in contract_set]
    if unexpected:
        raise SchemaValidationError(
            f"[{table}] {csv_path}: unexpected column(s) {unexpected} not in "
            f"contract. Rule: no-unexpected-columns. Allowed columns: {contract_names}."
        )

    # Rule 3 & 4: type conformance + allowed_values (only for present columns)
    by_name = {c["name"]: c for c in columns}
    for name in actual:
        spec = by_name[name]
        ctype = spec.get("type", "VARCHAR")
        expr = _parse_expr(name, ctype)
        if expr is not None:
            # A violation = a non-null raw value that fails to parse.
            bad = df.select(
                (pl.col(name).is_not_null() & expr.is_null()).sum().alias("n")
            ).item()
            if bad and bad > 0:
                sample_bad = (
                    df.filter(pl.col(name).is_not_null() & expr.is_null())
                    .select(name).head(1).item()
                )
                raise SchemaValidationError(
                    f"[{table}] {csv_path}: column '{name}' has {bad} value(s) "
                    f"that do not parse as {ctype} (e.g. {sample_bad!r}). "
                    f"Rule: type-conformance."
                )
        allowed = spec.get("allowed_values")
        if allowed:
            allowed_set = set(allowed)
            seen = (
                df.select(pl.col(name)).drop_nulls().unique().to_series().to_list()
            )
            invalid = [v for v in seen if v not in allowed_set]
            if invalid:
                raise SchemaValidationError(
                    f"[{table}] {csv_path}: column '{name}' has value(s) "
                    f"{invalid} outside allowed_values {allowed}. "
                    f"Rule: allowed-values."
                )
