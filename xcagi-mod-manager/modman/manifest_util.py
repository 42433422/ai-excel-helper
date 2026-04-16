"""与 XCAGI app.infrastructure.mods.manifest 字段对齐的校验与读写。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def read_manifest(mod_dir: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    p = mod_dir / "manifest.json"
    if not p.is_file():
        return None, f"缺少 manifest.json: {p}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"JSON 无效: {p}: {e}"
    if not isinstance(data, dict):
        return None, "manifest 根节点须为对象"
    return data, None


def validate_manifest_dict(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    mid = data.get("id")
    if not mid or not isinstance(mid, str) or not mid.strip():
        errors.append("缺少非空字符串字段 id")
    elif not re.match(r"^[a-z0-9][a-z0-9._-]*$", mid.strip()):
        errors.append(
            "id 建议使用小写字母、数字、点、下划线、连字符，且不以连字符开头"
        )
    for key in ("name", "version"):
        v = data.get(key)
        if v is None or (isinstance(v, str) and not v.strip()):
            errors.append(f"建议填写非空 {key}")
    be = data.get("backend") or {}
    if not isinstance(be, dict):
        errors.append("backend 须为对象")
    else:
        if not (be.get("entry") or "").strip():
            errors.append("backend.entry 建议填写（如 blueprints）")
        if not (be.get("init") or "").strip():
            errors.append("backend.init 建议填写（如 mod_init）")
    fe = data.get("frontend") or {}
    if not isinstance(fe, dict):
        errors.append("frontend 须为对象")
    else:
        if not (fe.get("routes") or "").strip():
            errors.append("frontend.routes 建议填写（相对 Mod 根的路径）")
    hooks = data.get("hooks")
    if hooks is not None and not isinstance(hooks, dict):
        errors.append("hooks 须为对象（可为空）")
    comms = data.get("comms")
    if comms is not None:
        if not isinstance(comms, dict):
            errors.append("comms 须为对象")
        else:
            ex = comms.get("exports")
            if ex is not None and not isinstance(ex, list):
                errors.append("comms.exports 须为数组")
    wf = data.get("workflow_employees")
    if wf is not None and not isinstance(wf, list):
        errors.append("workflow_employees 须为数组")
    return errors


def folder_name_must_match_id(mod_dir: Path, data: Dict[str, Any]) -> str | None:
    mid = (data.get("id") or "").strip()
    if not mid:
        return None
    if mod_dir.name != mid:
        return f"目录名 {mod_dir.name!r} 与 manifest id {mid!r} 不一致（XCAGI 按文件夹名加载）"
    return None


def write_manifest(mod_dir: Path, data: Dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    (mod_dir / "manifest.json").write_text(text, encoding="utf-8")


def save_manifest_validated(mod_dir: Path, data: Dict[str, Any]) -> List[str]:
    """
    写入完整 manifest：校验结构，且 manifest.id 必须与文件夹名一致。
    返回警告列表（可为空）；失败抛 ValueError。
    """
    mid = (data.get("id") or "").strip()
    if mid != mod_dir.name:
        raise ValueError(
            f"manifest.id 必须为 {mod_dir.name!r}（与目录名一致），当前为 {mid!r}"
        )
    ve = validate_manifest_dict(data)
    write_manifest(mod_dir, data)
    return ve


def patch_manifest_fields(mod_dir: Path, updates: Dict[str, Any]) -> Dict[str, Any]:
    data, err = read_manifest(mod_dir)
    if err or not data:
        raise ValueError(err or "无法读取 manifest")
    for k, v in updates.items():
        if v is None:
            continue
        if k in ("name", "version", "author", "description") and isinstance(v, str):
            data[k] = v
        elif k == "primary":
            data["primary"] = bool(v)
    write_manifest(mod_dir, data)
    return data
