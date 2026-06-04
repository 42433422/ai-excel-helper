"""从 zip 包（.xcmod / .xcemp）读取 manifest，供校验与分类型安装。"""

from __future__ import annotations

import json
import logging
import zipfile
from typing import Any

from .artifact_constants import normalize_artifact

logger = logging.getLogger(__name__)


def peek_manifest_from_zip(package_path: str) -> dict[str, Any]:
    """
    不解压到磁盘，从 zip 内读取 manifest.json（支持根级或唯一子目录/<id>/manifest.json）。
    """
    if not zipfile.is_zipfile(package_path):
        raise ValueError("不是有效的 zip 文件")
    with zipfile.ZipFile(package_path, "r") as zf:
        names = zf.namelist()
        if "manifest.json" in names:
            raw = zf.read("manifest.json").decode("utf-8")
            return json.loads(raw)
        candidates = [n for n in names if n.endswith("/manifest.json") and n.count("/") == 1]
        if len(candidates) == 1:
            raw = zf.read(candidates[0]).decode("utf-8")
            return json.loads(raw)
        if not candidates:
            raise ValueError("zip 内未找到 manifest.json")
        # 多个一级 manifest：取与 manifest.id 路径一致者
        for c in sorted(candidates):
            try:
                data = json.loads(zf.read(c).decode("utf-8"))
                mid = (data.get("id") or "").strip()
                if mid and c.startswith(mid + "/"):
                    return data
            except json.JSONDecodeError:
                continue
        raw = zf.read(sorted(candidates)[0]).decode("utf-8")
        return json.loads(raw)


def peek_artifact(package_path: str) -> str:
    data = peek_manifest_from_zip(package_path)
    return normalize_artifact(data)


def validate_bundle_manifest(manifest: dict[str, Any], depth: int = 0) -> list[str]:
    from .artifact_constants import ARTIFACT_BUNDLE, BUNDLE_MAX_DEPTH

    errs: list[str] = []
    if normalize_artifact(manifest) != ARTIFACT_BUNDLE:
        return errs
    if depth > BUNDLE_MAX_DEPTH:
        errs.append(f"bundle 嵌套深度超过上限 {BUNDLE_MAX_DEPTH}")
        return errs
    b = manifest.get("bundle")
    if not isinstance(b, dict):
        errs.append("artifact 为 bundle 时 bundle 须为对象")
        return errs
    contains = b.get("contains")
    embeds = b.get("embeds")
    if contains is not None and not isinstance(contains, list):
        errs.append("bundle.contains 须为数组")
    if embeds is not None and not isinstance(embeds, list):
        errs.append("bundle.embeds 须为数组")
    if not contains and not embeds:
        errs.append("bundle 至少需包含 contains 或 embeds 之一")
    if isinstance(contains, list):
        for i, item in enumerate(contains):
            if not isinstance(item, dict):
                errs.append(f"bundle.contains[{i}] 须为对象")
                continue
            if not (item.get("ref") or "").strip():
                errs.append(f"bundle.contains[{i}] 缺少 ref")
    if isinstance(embeds, list):
        for i, p in enumerate(embeds):
            if not isinstance(p, str) or not p.strip():
                errs.append(f"bundle.embeds[{i}] 须为非空相对路径字符串")
    return errs


def validate_xcagi_host_profile_extensions(manifest: dict[str, Any]) -> list[str]:
    """可选 ``xcagi_host_profile``：与 MODstore 生成契约对齐的轻量校验（未知字段不报错）。"""
    errs: list[str] = []
    hp = manifest.get("xcagi_host_profile")
    if hp is None:
        return errs
    if not isinstance(hp, dict):
        errs.append("xcagi_host_profile 须为对象")
        return errs
    allowed_kinds = {"builtin_track", "mod_http", "placeholder"}
    pk = str(hp.get("panel_kind") or "mod_http").strip()
    if pk not in allowed_kinds:
        errs.append(f"xcagi_host_profile.panel_kind 无效: {pk!r}")
    builtin = str(hp.get("builtin_track_id") or "").strip()
    allowed_builtin = {
        "label_print",
        "shipment_mgmt",
        "receipt_confirm",
        "wechat_msg",
        "wechat_phone",
        "real_phone",
    }
    if builtin and builtin not in allowed_builtin:
        errs.append(f"xcagi_host_profile.builtin_track_id 不在宿主白名单: {builtin!r}")
    if builtin and pk != "builtin_track":
        errs.append("填写 builtin_track_id 时 panel_kind 应为 builtin_track")
    row = hp.get("workflow_employee_row")
    if row is not None and not isinstance(row, dict):
        errs.append("xcagi_host_profile.workflow_employee_row 须为对象")
    return errs


def validate_employee_pack_manifest(manifest: dict[str, Any]) -> list[str]:
    from .artifact_constants import ARTIFACT_EMPLOYEE_PACK

    errs: list[str] = []
    if normalize_artifact(manifest) != ARTIFACT_EMPLOYEE_PACK:
        return errs
    emp = manifest.get("employee")
    if not isinstance(emp, dict):
        errs.append("employee_pack 须包含 employee 对象")
        return errs
    eid = (emp.get("id") or "").strip()
    if not eid:
        errs.append("employee.id 不能为空")
    scope = (manifest.get("scope") or "global").strip().lower()
    if scope not in {"global", "host"}:
        errs.append("scope 仅支持 global 或 host（预留 host_mod 二期）")
    if scope == "host" and not (manifest.get("host_mod") or "").strip():
        errs.append("scope=host 时需填写 host_mod（二期启用）")
    errs.extend(validate_xcagi_host_profile_extensions(manifest))
    return errs
