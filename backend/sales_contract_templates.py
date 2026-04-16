"""
销售合同 Word 模板：仅允许仓库内 ``424/`` 下已登记文件，供前端下拉与生成接口闭环。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def fhd_repo_root() -> Path:
    """仓库根（``backend`` 的上一级）。"""
    return Path(__file__).resolve().parents[1]


# (模板 id, 相对仓库根路径, 界面展示名称) — 路径必须位于 424/ 下
INTERNAL_SALES_CONTRACT_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("pzmob", "424/PZMOB.docx", "购销 / PZMOB"),
    ("sales_cn", "424/templates/销售合同模板.docx", "销售合同（中文文件名）"),
)


def _relpath_allowed(rel: str) -> bool:
    p = Path(rel)
    if ".." in p.parts:
        return False
    return len(p.parts) >= 1 and p.parts[0] == "424"


def _is_under_repo(abs_path: Path, repo: Path) -> bool:
    try:
        abs_path.resolve().relative_to(repo.resolve())
        return True
    except ValueError:
        return False


def list_internal_sales_contract_templates() -> list[dict[str, Any]]:
    """返回当前磁盘上存在的内部模板（供 GET /api/sales-contract/templates）。"""
    repo = fhd_repo_root()
    out: list[dict[str, Any]] = []
    for tid, rel, label in INTERNAL_SALES_CONTRACT_TEMPLATES:
        if not _relpath_allowed(rel):
            continue
        p = (repo / rel).resolve()
        if not p.is_file() or not _is_under_repo(p, repo):
            continue
        out.append({"id": tid, "label": label, "path": rel})
    return out


def resolve_sales_contract_template_file(template_id: str | None) -> tuple[Path | None, str | None]:
    """
    解析模板路径，返回 ``(绝对路径, 实际使用的模板 id)``。

    1. ``template_id`` 在登记表中且文件存在 → 使用该内部文件
    2. 否则使用登记表中**第一个**存在的内部文件
    3. 若内部均无文件，回退 ``FHD_SALES_CONTRACT_TEMPLATE``（运维覆盖，此时第二项为 ``"env"``）
    """
    repo = fhd_repo_root()
    available = list_internal_sales_contract_templates()
    by_id = {str(x["id"]): str(x["path"]) for x in available}
    tid = (template_id or "").strip()
    if tid and tid in by_id:
        p = (repo / by_id[tid]).resolve()
        if p.is_file() and _is_under_repo(p, repo):
            return p, tid
    for row in available:
        p = (repo / row["path"]).resolve()
        if p.is_file() and _is_under_repo(p, repo):
            return p, str(row["id"])

    env = (os.environ.get("FHD_SALES_CONTRACT_TEMPLATE") or "").strip()
    if env:
        ep = Path(env).expanduser()
        if ep.is_file():
            return ep, "env"
    return None, None
