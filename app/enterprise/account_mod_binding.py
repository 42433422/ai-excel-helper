"""本机/演示账号与客户 Mod 的固定绑定（修茈市场未返回 user_mods 时的兜底）。"""

from __future__ import annotations

from app.mod_sdk.platform_shell import PROTECTED_CLIENT_MOD_IDS

# 太阳鸟演示账号（见 alembic seed SUNBIRD）
SUNBIRD_LOCAL_USERNAMES: frozenset[str] = frozenset({"SUNBIRD", "sunbird"})
SUNBIRD_CLIENT_MOD_ID = "taiyangniao-pro"


def is_sunbird_local_username(username: str) -> bool:
    u = (username or "").strip()
    return u.upper() in {x.upper() for x in SUNBIRD_LOCAL_USERNAMES}


def augment_entitled_client_mod_ids_for_username(
    username: str,
    current: set[str] | None = None,
) -> set[str]:
    """在已有权益集上合并账号级默认客户 Mod。"""
    out = set(current or ())
    if is_sunbird_local_username(username):
        if SUNBIRD_CLIENT_MOD_ID in PROTECTED_CLIENT_MOD_IDS:
            out.add(SUNBIRD_CLIENT_MOD_ID)
    return out
