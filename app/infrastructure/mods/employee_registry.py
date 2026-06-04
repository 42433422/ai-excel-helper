"""全局 AI 员工包（employee_pack）安装目录：mods/_employees/<pack_id>/。"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from typing import Any

from .artifact_constants import ARTIFACT_EMPLOYEE_PACK, normalize_artifact
from .artifact_package import validate_employee_pack_manifest
from .package import ModPackage, ModPackageError, ModSignatureError

logger = logging.getLogger(__name__)

_EMP_DIR = "_employees"


def employees_root(mods_root: str) -> str:
    return os.path.join(mods_root, _EMP_DIR)


class EmployeeRegistry:
    def __init__(self, mods_root: str):
        self.mods_root = os.path.abspath(mods_root)

    def _root(self) -> str:
        return employees_root(self.mods_root)

    def list_packs(self) -> list[dict[str, Any]]:
        root = self._root()
        if not os.path.isdir(root):
            return []
        out: list[dict[str, Any]] = []
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if not os.path.isdir(p):
                continue
            mf = os.path.join(p, "manifest.json")
            if not os.path.isfile(mf):
                continue
            try:
                with open(mf, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if normalize_artifact(data) != ARTIFACT_EMPLOYEE_PACK:
                continue
            emp = data.get("employee") if isinstance(data.get("employee"), dict) else {}
            out.append(
                {
                    "pack_id": name,
                    "id": data.get("id", name),
                    "name": data.get("name", ""),
                    "version": data.get("version", ""),
                    "author": data.get("author", ""),
                    "description": data.get("description", ""),
                    "employee": emp,
                    "xcagi_host_profile": data.get("xcagi_host_profile"),
                }
            )
        return out

    def list_for_mods_api(self) -> list[dict[str, Any]]:
        """与 ModManager._metadata_to_api_dict 形状兼容，供 /api/mods/ 合并。"""
        rows: list[dict[str, Any]] = []
        for p in self.list_packs():
            emp = dict(p.get("employee") or {}) if isinstance(p.get("employee"), dict) else {}
            hp = p.get("xcagi_host_profile")
            if isinstance(hp, dict):
                wer = hp.get("workflow_employee_row")
                if isinstance(wer, dict):
                    for k, v in wer.items():
                        ks = str(k)
                        if ks not in emp or emp.get(ks) in (None, ""):
                            emp[ks] = v
            wf = [emp] if emp.get("id") else []
            rows.append(
                {
                    "id": str(p.get("id") or p.get("pack_id") or ""),
                    "name": str(p.get("name") or ""),
                    "version": str(p.get("version") or ""),
                    "author": str(p.get("author") or ""),
                    "description": str(p.get("description") or ""),
                    "primary": False,
                    "type": "employee_pack",
                    "menu": [],
                    "workflow_employees": wf,
                    "comms_exports": [],
                }
            )
        return rows

    def install_from_package(
        self,
        package_path: str,
        verify_signature: bool = True,
    ) -> tuple[bool, str]:
        if not os.path.isfile(package_path):
            return False, "文件不存在"
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_path, manifest = ModPackage.extract_package(
                    package_path, temp_dir, verify_signature=verify_signature
                )
                if normalize_artifact(manifest) != ARTIFACT_EMPLOYEE_PACK:
                    return False, "非 employee_pack 包"
                ve = validate_employee_pack_manifest(manifest)
                if ve:
                    return False, "; ".join(ve)
                scope = str(manifest.get("scope") or "global").strip().lower()
                if scope != "global":
                    return False, "当前仅支持 scope=global 的员工包安装"
                pack_id = (manifest.get("id") or "").strip()
                if not pack_id:
                    return False, "缺少 id"
                dest = os.path.join(self._root(), pack_id)
                os.makedirs(self._root(), exist_ok=True)
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(extract_path, dest)
                logger.info("Installed employee_pack to %s", dest)
                return True, f"员工包 {pack_id} 安装成功"
        except ModSignatureError as e:
            return False, f"签名验证失败：{e}"
        except ModPackageError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("employee pack install failed")
            return False, str(e)

    def uninstall_pack(self, pack_id: str, remove_files: bool = True) -> tuple[bool, str]:
        pack_id = (pack_id or "").strip()
        if not pack_id or "/" in pack_id or "\\" in pack_id:
            return False, "非法 pack id"
        dest = os.path.join(self._root(), pack_id)
        if not os.path.isdir(dest):
            return False, f"员工包未安装：{pack_id}"
        if remove_files:
            shutil.rmtree(dest, ignore_errors=True)
        return True, f"员工包 {pack_id} 已卸载"


_registry: dict[str, EmployeeRegistry] = {}


def get_employee_registry(mods_root: str | None = None) -> EmployeeRegistry:
    from .mod_manager import _default_mods_root

    root = mods_root or _default_mods_root()
    key = os.path.abspath(root)
    r = _registry.get(key)
    if r is None:
        r = EmployeeRegistry(key)
        _registry[key] = r
    return r
