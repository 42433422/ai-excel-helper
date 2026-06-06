"""开发/启动时幂等创建 PostgreSQL 按 Mod 分库（与 scripts/bootstrap_mod_dbs.py 一致）。"""

from __future__ import annotations

import importlib.util
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_bootstrap_module():
    path = _REPO_ROOT / "scripts" / "bootstrap_mod_dbs.py"
    spec = importlib.util.spec_from_file_location("xcagi_bootstrap_mod_dbs", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mod_isolated_enabled() -> bool:
    return (os.environ.get("XCAGI_MOD_ISOLATED_DATABASES") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def ensure_postgres_per_mod_databases(
    *,
    mod_ids: list[str] | None = None,
    migrate_new: bool = True,
) -> list[str]:
    """
    为缺失的 ``{base}__{mod_suffix}`` 建空库并（可选）对该库执行 ``alembic upgrade head``。

    Returns:
        本次新建的库名列表。
    """
    if not _mod_isolated_enabled():
        return []

    base_url = (os.environ.get("DATABASE_URL") or "").strip()
    if not base_url.startswith("postgresql") and not base_url.startswith("postgres"):
        return []

    boot = _load_bootstrap_module()
    ids = mod_ids or boot._discover_mod_ids()
    if not ids:
        return []

    clone_mod_ids = set(getattr(boot, "DEFAULT_CLONE_FROM_BASE_MOD_IDS", ()) or ())

    from sqlalchemy.engine import make_url

    base_u = make_url(base_url)
    base_db = (base_u.database or "xcagi").strip()
    owner = base_u.username or None

    admin_engine = boot._maintenance_engine(base_url)
    created_dbnames: list[str] = []

    try:
        with admin_engine.connect() as conn:
            if not boot._db_exists(conn, base_db):
                logger.warning(
                    "ensure_postgres_per_mod_databases: base database %s missing, skip mod DBs",
                    base_db,
                )
                return []

            for mid in ids:
                suf = boot._normalize_mod_file_suffix(mid)
                if not suf:
                    continue
                dbn = f"{base_db}__{suf}"
                if boot._db_exists(conn, dbn):
                    continue
                if mid in clone_mod_ids:
                    logger.info("Cloning mod database from base: %s (mod=%s)", dbn, mid)
                    boot._create_db_from_template(conn, dbn, base_db, owner)
                else:
                    logger.info("Creating empty mod database: %s (mod=%s)", dbn, mid)
                    boot._create_db_empty(conn, dbn, owner)
                created_dbnames.append(dbn)
    finally:
        admin_engine.dispose()

    for dbn in created_dbnames:
        mod_url = boot._url_for_database(base_u, dbn)
        boot._enable_pgvector(mod_url, dbn)

    # 自基库克隆的库已含完整 schema，无需再跑 alembic
    to_migrate: list[str] = []
    for mid in ids:
        if mid in clone_mod_ids:
            continue
        suf = boot._normalize_mod_file_suffix(mid)
        if not suf:
            continue
        dbn = f"{base_db}__{suf}"
        if dbn in created_dbnames:
            to_migrate.append(dbn)

    if migrate_new and to_migrate:
        _migrate_mod_databases(to_migrate, mod_ids=ids)

    return created_dbnames


def _migrate_mod_databases(only_dbnames: list[str] | None, *, mod_ids: list[str]) -> None:
    """对指定 mod 库跑迁移；``only_dbnames`` 为空则迁移全部已发现 mod。"""
    boot = _load_bootstrap_module()
    base_url = (os.environ.get("DATABASE_URL") or "").strip()
    from sqlalchemy.engine import make_url

    base_u = make_url(base_url)
    base_db = (base_u.database or "xcagi").strip()
    alembic_ini = _REPO_ROOT / "alembic.ini"
    if not alembic_ini.is_file():
        logger.warning("alembic.ini not found at %s; skip mod migrations", alembic_ini)
        return

    target_set = set(only_dbnames or [])
    for mid in mod_ids:
        suf = boot._normalize_mod_file_suffix(mid)
        if not suf:
            continue
        dbn = f"{base_db}__{suf}"
        if target_set and dbn not in target_set:
            continue
        mod_url = boot._url_for_database(base_u, dbn)
        env = os.environ.copy()
        env["DATABASE_URL"] = mod_url
        logger.info("alembic upgrade head -> %s", dbn)
        r = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
            cwd=str(_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            logger.error(
                "mod migration failed for %s (exit %s): %s",
                dbn,
                r.returncode,
                (r.stderr or r.stdout or "")[:2000],
            )
        else:
            logger.info("mod migration OK: %s", dbn)
