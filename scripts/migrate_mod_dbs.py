#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对每个扩展库 {基库名}__<mod_suffix> 依次执行 alembic upgrade head。

前置：
    - DATABASE_URL 指向基库（脚本会改写 URL 的 database 部分逐个迁移）
    - 已运行 scripts/bootstrap_mod_dbs.py 建好各 Mod 库
    - FHD 根目录下的 alembic.ini 与 alembic/env.py 可用

用法（仓库根目录）：
    python scripts/migrate_mod_dbs.py

对 sz-qsm-pro：由于 bootstrap 阶段是用 TEMPLATE 克隆，alembic_version 表
已有与基库一致的版本号，upgrade head 天然 no-op。
可以用 --skip sz-qsm-pro 跳过，或 --stamp-only sz-qsm-pro 只做 stamp。
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_bootstrap_module():
    path = _ROOT / "scripts" / "bootstrap_mod_dbs.py"
    spec = importlib.util.spec_from_file_location("xcagi_bootstrap_mod_dbs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/bootstrap_mod_dbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--skip", action="append", default=[], help="跳过的 mod id，可多次传")
    parser.add_argument(
        "--stamp-only",
        action="append",
        default=[],
        help="对该 mod 只做 alembic stamp head，可多次传",
    )
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv

        load_dotenv(_ROOT / ".env")
    except ImportError:
        pass

    boot = _load_bootstrap_module()

    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not (url.startswith("postgresql") or url.startswith("postgres")):
        print("ERROR: DATABASE_URL must be PostgreSQL.", file=sys.stderr)
        return 1

    flag = (os.environ.get("XCAGI_MOD_ISOLATED_DATABASES") or "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        print(
            "NOTE: XCAGI_MOD_ISOLATED_DATABASES not enabled in env; "
            "本脚本仍会直接连各 mod 库执行迁移（不依赖该开关）。",
            file=sys.stderr,
        )

    mod_ids = boot._discover_mod_ids()
    if not mod_ids:
        print(
            "ERROR: No mod ids found (XCAGI_MOD_DATABASE_URLS / XCAGI_MOD_IDS / mods/*/manifest.json).",
            file=sys.stderr,
        )
        return 1

    from sqlalchemy.engine import make_url

    base_u = make_url(url)
    base_db = (base_u.database or "xcagi").strip()

    def url_for_database(dbname: str) -> str:
        return base_u.set(database=dbname).render_as_string(hide_password=False)

    alembic_ini = _ROOT / "alembic.ini"
    if not alembic_ini.is_file():
        print(f"ERROR: alembic.ini not found at {alembic_ini}", file=sys.stderr)
        return 1

    skip_set = {str(s).strip() for s in (args.skip or []) if str(s).strip()}
    stamp_only_set = {str(s).strip() for s in (args.stamp_only or []) if str(s).strip()}

    print("============================================================")
    print(" migrate_mod_dbs.py")
    print(f" base database: {base_db}")
    print(f" mods:          {', '.join(mod_ids)}")
    if skip_set:
        print(f" skip:          {', '.join(sorted(skip_set))}")
    if stamp_only_set:
        print(f" stamp-only:    {', '.join(sorted(stamp_only_set))}")
    print("============================================================")

    rc = 0
    for mid in mod_ids:
        if mid in skip_set:
            print(f"SKIP (requested): {mid}")
            continue
        suf = boot._normalize_mod_file_suffix(mid)
        if not suf:
            continue
        dbn = f"{base_db}__{suf}"
        mod_url = url_for_database(dbn)
        env = os.environ.copy()
        env["DATABASE_URL"] = mod_url

        if mid in stamp_only_set:
            print(f"==> alembic stamp head  ->  {dbn}")
            cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "stamp", "head"]
        else:
            print(f"==> alembic upgrade head  ->  {dbn}")
            cmd = [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"]

        r = subprocess.run(cmd, cwd=str(_ROOT), env=env)
        if r.returncode != 0:
            rc = r.returncode
            print(f"FAILED: {dbn} (exit {r.returncode})", file=sys.stderr)

    if rc == 0:
        print("\nAll per-mod migrations done.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
