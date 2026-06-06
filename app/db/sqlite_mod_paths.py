"""SQLite 文件名与当前扩展 Mod 对齐（与 app.db 中 DATABASE_URL 改写规则一致）。"""

from __future__ import annotations

from pathlib import Path


def mod_suffix_token(mod_id: str) -> str:
    return (
        "".join(ch if ch.isalnum() else "_" for ch in str(mod_id or "").strip()).strip("_").lower()
    )


def sqlite_filename_with_mod_suffix(filename: str, mod_id: str) -> str:
    """
    例如 products.db + taiyangniao-pro -> products__taiyangniao_pro.db
    与 _sqlite_url_with_mod_suffix 使用相同的 stem 规则。
    """
    if not mod_id or not filename:
        return filename
    p = Path(filename)
    if not p.name or p.suffix == "":
        return filename
    suffix = mod_suffix_token(mod_id)
    if not suffix:
        return filename
    return p.with_name(f"{p.stem}__{suffix}{p.suffix}").name
