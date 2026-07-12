# HR Analytics Command Center - Governance Rules

All contributors and automation agents must follow these project governance rules.

- No real HR employee data may be accessed, requested, created, processed, inspected, loaded, or exposed.
- No live system connections may be made.
- No credentials, tokens, API keys, passwords, database URLs, or production connection strings may be added.
- No files may be added or modified inside `data/real_*` except existing `.gitkeep` files.
- No real-data load may be scheduled or executed.
- No load scheduling may be performed.
- No real communications may be sent.
- No actual Go/No-Go meeting may be held.
- No actual real-data execution may be approved.
- Human review is required before merge.

**Scope of the above rules.** The prohibitions above govern (a) anything committed to this repository and (b) the shared synthetic governance simulation (`data/real_*`, `data/synthetic_dry_run/`, the Gate 1–5 artifacts). They do **not** prohibit a single operator running the dashboard **locally** on real HR data that is **never committed, never pushed, never deployed, and confined to gitignored paths** (`data/raw/`, `data/bronze/`, `data/silver/`, `data/gold/`, `warehouse/`). Local real-data use must leave the committed tree, CI, and `data/sample/` unchanged; the `data/real_*` directories remain simulation-only and stay `.gitkeep`-only.
