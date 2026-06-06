#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 XCAGI_MOD_ISOLATED_DATABASES 开启后，不同 mod 会被路由到不同 PG 库且能读到各自数据。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv  # type: ignore[import-not-found]

load_dotenv(_ROOT / ".env")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.infrastructure.db.sync_engine import resolve_database_url_for_active_mod  # noqa: E402
from app.request_active_mod_ctx import set_request_active_mod_id  # noqa: E402


MODS = ["taiyangniao-pro"]


def _probe(url: str) -> dict:
    out: dict = {"db": make_url(url).database}
    eng = create_engine(url, future=True)
    try:
        with eng.connect() as c:
            out["products"] = int(c.execute(text("SELECT count(*) FROM products")).scalar() or 0)
            out["alembic_heads"] = int(
                c.execute(text("SELECT count(*) FROM alembic_version")).scalar() or 0
            )
    finally:
        eng.dispose()
    return out


def main() -> int:
    base = (os.environ.get("DATABASE_URL") or "").strip()
    if not base:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    isolated = (os.environ.get("XCAGI_MOD_ISOLATED_DATABASES") or "").strip().lower()

    print(f"DATABASE_URL             = {make_url(base).render_as_string(hide_password=True)}")
    print(f"XCAGI_MOD_ISOLATED_DATABASES = {isolated or '(unset)'}")
    print()

    print("[shell / no active mod]")
    set_request_active_mod_id("")
    url = resolve_database_url_for_active_mod(base)
    print(f"  resolved -> {make_url(url).database}")
    print(f"  probe    -> {_probe(url)}")
    print()

    ok = True
    for mid in MODS:
        print(f"[mod={mid}]")
        set_request_active_mod_id(mid)
        url = resolve_database_url_for_active_mod(base)
        print(f"  resolved -> {make_url(url).database}")
        try:
            info = _probe(url)
            print(f"  probe    -> {info}")
        except Exception as exc:
            ok = False
            print(f"  probe FAILED: {exc}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
