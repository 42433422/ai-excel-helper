#!/usr/bin/env python3
"""
Unified script template for tools/.

Usage:
    python tools/<category>/<your_script>.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ScriptResult:
    success: bool
    message: str
    processed: int = 0
    changed: int = 0
    failed: int = 0
    extra: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool script template with dry-run and summary output."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without persisting changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run(*, dry_run: bool) -> ScriptResult:
    """
    Implement script logic here.

    Rules:
    - keep side effects explicit
    - respect dry_run for all writes
    - return ScriptResult with key metrics
    """
    logging.info("Template run started (dry_run=%s)", dry_run)

    # Example counters. Replace with real logic.
    processed = 0
    changed = 0
    failed = 0

    # TODO: Implement script-specific logic.

    return ScriptResult(
        success=True,
        message="Template executed. Replace run() with real logic.",
        processed=processed,
        changed=changed,
        failed=failed,
        extra={"dry_run": dry_run},
    )


def print_summary(result: ScriptResult, started_at: datetime) -> None:
    duration = (datetime.now() - started_at).total_seconds()
    print("\n=== SCRIPT SUMMARY ===")
    print(f"success:   {result.success}")
    print(f"message:   {result.message}")
    print(f"processed: {result.processed}")
    print(f"changed:   {result.changed}")
    print(f"failed:    {result.failed}")
    if result.extra:
        print(f"extra:     {result.extra}")
    print(f"duration:  {duration:.2f}s")


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    started_at = datetime.now()

    try:
        result = run(dry_run=args.dry_run)
        print_summary(result, started_at)
        return 0 if result.success else 1
    except Exception as exc:
        logging.error("Script failed with unhandled exception: %s", exc)
        logging.debug(traceback.format_exc())
        print("\n=== SCRIPT SUMMARY ===")
        print("success:   False")
        print(f"message:   Unhandled exception: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
