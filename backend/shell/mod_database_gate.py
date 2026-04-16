"""
Mod 门禁与（可选）数据库连接串「加密藏起来」。

- ``FHD_DB_MOD_GATE``：逗号分隔的 mod ``id``；须全部出现在 ``mods_catalog.list_mod_items()``
  返回的列表中，才允许解析 ``DATABASE_URL`` / 建连 PostgreSQL。
- ``FHD_DB_URL_ENCRYPT_ON_GATE_FAIL=1`` 且设置 ``FHD_DB_GATE_SECRET``（任意非空字符串，内部 SHA256 派生 Fernet 密钥）：
  门禁未通过时，将 ``DATABASE_URL`` 加密写入 ``FHD_DB_URL_CIPHER_FILE``（默认
  ``<tempdir>/fhd_dburl.fernet``），并从环境中 **删除** 明文；门禁通过后再解密写回环境变量
  仅驻内存（不落盘明文）。

依赖 ``cryptography``；未安装时跳过加密步骤并打 warning。

种子 SQL：

- 单文件：``database_seed_sql``（manifest 内可为相对 mod 目录路径），门禁通过后执行一次。
- 多文件：``database_seed_files`` 字符串数组，或 ``database.seed_files``（与 ``frontend.menu`` 嵌套风格一致），
  路径均相对 mod 根目录；在 ``database_seed_sql`` 之后按数组顺序执行。
- 说明字段：``database_notes`` 或 ``database.notes_zh``，仅用于 API / 设置页展示。

**分库说明**：宿主进程仍为单一 ``DATABASE_URL``，上述种子打到**同一** PostgreSQL。若各 Mod 必须物理隔离，
请为每个部署配置不同的 ``DATABASE_URL``（不同库名）并分别启动进程；manifest 只描述本包种子与说明。

**共库多扩展**：表 ``products`` / ``purchase_units`` / ``customers`` 可选列 ``xcagi_mod_id``（见
``scripts/pg_init_xcagi_core.sql`` 与 ``ensure_mod_row_scope_columns``）；请求头 ``X-XCAGI-Active-Mod-Id``
与 ``backend.shell.mod_row_scope`` 在读写时按该列过滤，避免侧栏已选 A 包却读到 B 包主数据。
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Any

from backend.shell.mods_catalog import list_mod_items

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_fernet_stash_done = False
_seed_applied: set[str] = set()


def required_mod_ids() -> list[str]:
    raw = os.environ.get("FHD_DB_MOD_GATE", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def mod_db_gate_open() -> bool:
    reqs = required_mod_ids()
    if not reqs:
        return True
    loaded = {m.id for m in list_mod_items()}
    return all(r in loaded for r in reqs)


def _fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def cipher_file_path() -> Path:
    p = os.environ.get("FHD_DB_URL_CIPHER_FILE", "").strip()
    if p:
        return Path(p).expanduser().resolve()
    import tempfile

    return Path(tempfile.gettempdir()) / "fhd_dburl.fernet"


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def maybe_encrypt_database_url_when_gate_closed() -> None:
    """
    门禁关闭且允许加密时：把 DATABASE_URL 加密写入密文文件并删除环境变量中的明文。
    幂等：已执行过则不再写。
    """
    global _fernet_stash_done
    if mod_db_gate_open():
        return
    if not _truthy("FHD_DB_URL_ENCRYPT_ON_GATE_FAIL"):
        return
    secret = os.environ.get("FHD_DB_GATE_SECRET", "").strip()
    if not secret:
        logger.warning("FHD_DB_URL_ENCRYPT_ON_GATE_FAIL 已开启但未设置 FHD_DB_GATE_SECRET，跳过加密")
        return
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return
    with _lock:
        if _fernet_stash_done:
            return
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            logger.warning("未安装 cryptography，无法加密 DATABASE_URL；请 pip install cryptography")
            return
        f = Fernet(_fernet_key_from_secret(secret))
        blob = f.encrypt(url.encode("utf-8"))
        out = cipher_file_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        os.environ.pop("DATABASE_URL", None)
        _fernet_stash_done = True
        logger.warning(
            "数据库门禁未通过：已将 DATABASE_URL 加密写入 %s 并从环境变量移除（进程内不再可见明文）。"
            " 门禁通过后将自动解密到内存。",
            out,
        )


def maybe_decrypt_database_url_when_gate_open() -> None:
    """门禁通过且环境变量无 DATABASE_URL 时，从密文文件解密写回环境（仅内存）。"""
    if not mod_db_gate_open():
        return
    if os.environ.get("DATABASE_URL", "").strip():
        return
    secret = os.environ.get("FHD_DB_GATE_SECRET", "").strip()
    if not secret:
        return
    path = cipher_file_path()
    if not path.is_file():
        return
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return
    try:
        raw = Fernet(_fernet_key_from_secret(secret)).decrypt(path.read_bytes()).decode("utf-8")
    except Exception as e:
        logger.error("解密 DATABASE_URL 失败（检查 FHD_DB_GATE_SECRET 或与密文文件是否匹配）: %s", e)
        return
    os.environ["DATABASE_URL"] = raw


def enforce_mod_database_gate_for_url() -> None:
    """
    在读取 ``DATABASE_URL`` 之前调用：先尝试解密；若门禁仍关闭则加密（可选）并抛错，
    避免回退到 ``FHD_DEFAULT_DATABASE_URL`` 造成「无 Mod 仍能连库」。
    """
    maybe_decrypt_database_url_when_gate_open()
    reqs = required_mod_ids()
    if not reqs:
        return
    if mod_db_gate_open():
        return
    maybe_encrypt_database_url_when_gate_closed()
    raise RuntimeError(
        "database_mod_gate_closed: 已配置 FHD_DB_MOD_GATE=%r，但当前壳层 mod 列表中未全部包含。"
        " 请部署对应 Mod 并更新 fhd_shell_mods.json（或 FHD_SHELL_MODS_JSON），或临时取消 FHD_DB_MOD_GATE。"
        % (",".join(reqs),)
    )


def mod_database_seed_plan_dict() -> dict[str, Any]:
    """
    供 ``get_db_status`` / 设置页展示：当前壳层扫描到的各 Mod 种子 SQL 路径（不要求已建连）。
    """
    try:
        items = list_mod_items()
    except Exception as e:
        return {"mods": [], "error": str(e), "architecture_note_zh": _architecture_note_zh()}

    mods: list[dict[str, Any]] = []
    for m in items:
        seeds: list[dict[str, str]] = []
        p0 = (m.database_seed_sql or "").strip()
        if p0:
            seeds.append({"role": "database_seed_sql", "path": p0})
        for i, p in enumerate(m.database_seed_files or []):
            ps = (p or "").strip()
            if ps:
                seeds.append({"role": f"seed_file_{i + 1}", "path": ps})
        if not seeds:
            continue
        note = (m.database_notes or "").strip() or None
        mods.append({"mod_id": m.id, "database_notes": note, "seeds": seeds})
    return {"mods": mods, "architecture_note_zh": _architecture_note_zh()}


def _architecture_note_zh() -> str:
    return (
        "宿主使用单一 DATABASE_URL：各 Mod 的种子 SQL 依次作用于同一 PostgreSQL。"
        "若需各 Mod 完全不同库，请为每个环境单独配置 DATABASE_URL 并分别启动后端实例。"
    )


def mod_database_gate_status() -> dict:
    reqs = required_mod_ids()
    return {
        "required_mod_ids": reqs,
        "gate_open": mod_db_gate_open() if reqs else True,
        "encrypt_on_gate_fail": _truthy("FHD_DB_URL_ENCRYPT_ON_GATE_FAIL"),
        "cipher_file": str(cipher_file_path()) if _truthy("FHD_DB_URL_ENCRYPT_ON_GATE_FAIL") else None,
        "database_url_in_env": bool(os.environ.get("DATABASE_URL", "").strip()),
    }


def _exec_one_seed_sql_file(engine, path: Path, mod_id: str, label: str) -> None:
    p = str(path)
    if p in _seed_applied:
        return
    if not path.is_file():
        logger.warning("%s 跳过（文件不存在）: %s", label, path)
        _seed_applied.add(p)
        return
    try:
        sql = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("读取 seed SQL 失败 %s: %s", path, e)
        _seed_applied.add(p)
        return
    if not sql.strip():
        _seed_applied.add(p)
        return
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
        logger.info("已执行 mod 种子 SQL: %s (mod=%s, %s)", path, mod_id, label)
    except Exception as e:
        logger.error("执行 mod 种子 SQL 失败 %s: %s", path, e)
        raise
    _seed_applied.add(p)


def apply_mod_database_seeds(engine) -> None:
    """对 ``database_seed_sql`` + ``database_seed_files`` 执行 SQL 文件（按 mod 列表顺序；路径幂等去重）。"""
    if not mod_db_gate_open():
        return
    for m in list_mod_items():
        mid = str(m.id or "").strip() or "?"
        paths: list[Path] = []
        p0 = (m.database_seed_sql or "").strip()
        if p0:
            paths.append(Path(p0))
        for p in m.database_seed_files or []:
            ps = (p or "").strip()
            if not ps:
                continue
            pp = Path(ps)
            if str(pp) not in {str(x) for x in paths}:
                paths.append(pp)
        for idx, path in enumerate(paths):
            label = "database_seed_sql" if idx == 0 else "database_seed_files"
            _exec_one_seed_sql_file(engine, path, mid, label)
