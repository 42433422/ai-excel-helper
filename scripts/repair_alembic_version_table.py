#!/usr/bin/env python3
"""
Repair alembic_version when ancestor + descendant revisions are both stamped.

Symptom::

    Requested revision xcagi_v5_approval_system overlaps with other requested revisions f0c2a8e1_templates

Cause: ``alembic_version`` contains two IDs on the same lineage (e.g. parent and child).
Upgrade computes closures with ``check=True`` and rejects that combination.

``alembic current`` can still show a single row because it filters to branch tips via
``get_all_current``; the raw table keeps redundant ancestor rows.

Usage (from repo ``FHD/``)::

    python scripts/repair_alembic_version_table.py          # dry-run: print DELETE plan
    python scripts/repair_alembic_version_table.py --apply

Uses ``DATABASE_URL`` like ``alembic/env.py`` (default local Postgres).
"""

from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://xcagi:xcagi@localhost:5432/xcagi",
    )


def _redundant_ancestor_ids(script: ScriptDirectory, stamped: list[str]) -> set[str]:
    """Revision IDs that are strict ancestors of another stamped revision."""
    rm = script.revision_map
    objs = []
    for vid in stamped:
        try:
            objs.append(rm.get_revision(vid))
        except Exception as exc:
            raise SystemExit(f"Unknown revision in alembic_version: {vid!r} ({exc})") from exc

    redundant: set[str] = set()
    for ra in objs:
        for rb in objs:
            if ra.revision == rb.revision:
                continue
            descendants = {
                r.revision for r in rm._get_descendant_nodes([ra], include_dependencies=True)
            }
            if rb.revision in descendants:
                redundant.add(ra.revision)
    return redundant


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate alembic_version lineage rows.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute DELETEs; default is dry-run only.",
    )
    args = parser.parse_args()

    cfg_path = os.path.join(_ROOT, "alembic.ini")
    cfg = Config(cfg_path)
    script = ScriptDirectory.from_config(cfg)

    url = _database_url()
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = [
            str(r[0])
            for r in conn.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
        ]
        if len(rows) <= 1:
            print(f"alembic_version: {len(rows)} row(s); nothing to repair.")
            return

        print(f"alembic_version ({len(rows)} rows): {rows}")
        kill = _redundant_ancestor_ids(script, rows)
        if not kill:
            print("No redundant ancestor stamps detected (parallel branches only).")
            return

        kept = [r for r in rows if r not in kill]
        print(f"Will remove ancestor row(s): {sorted(kill)}")
        print(f"Remaining row(s): {kept}")

        if not args.apply:
            print("Dry-run: pass --apply to execute DELETE.")
            return

        for vid in sorted(kill):
            conn.execute(text("DELETE FROM alembic_version WHERE version_num = :v"), {"v": vid})
        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()
