# Tools Directory

`tools/` is the only place for operational and temporary scripts that are still active.

## Subdirectories

- `tools/debug/`: diagnostics and investigation scripts.
- `tools/migrations/`: data/schema migration scripts.
- `tools/ops/`: operational scripts for maintenance and housekeeping.
- `tools/templates/`: reusable script templates.

## Rules

- New temporary scripts must be created under `tools/`, not business directories.
- Historical one-off scripts should be moved to `archive/`.
- Prefer CLI scripts with explicit arguments and `--dry-run` support.
- Print a short result summary at the end.

## How to Start a New Script

1. Copy `tools/templates/script_template.py`.
2. Rename it under one of `debug/`, `migrations/`, or `ops/`.
3. Implement the `run()` function and keep the CLI contract.
