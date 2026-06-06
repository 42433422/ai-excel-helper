"""按 artifact 分发安装；解析 bundle.embeds / bundle.contains（浅层顺序，无环校验）。"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from typing import Any

from .artifact_constants import (
    ARTIFACT_BUNDLE,
    ARTIFACT_EMPLOYEE_PACK,
    BUNDLE_MAX_DEPTH,
)
from .artifact_package import peek_artifact, validate_bundle_manifest
from .employee_registry import get_employee_registry
from .mod_manager import get_mod_manager
from .package import ModPackage, ModPackageError, ModSignatureError

logger = logging.getLogger(__name__)


def _find_package_in_store(store_dir: str, ref_id: str) -> str | None:
    if not store_dir or not os.path.isdir(store_dir):
        return None
    ref_id = ref_id.strip()
    best: str | None = None
    for name in os.listdir(store_dir):
        if not (name.endswith(".xcmod") or name.endswith(".xcemp")):
            continue
        if name.startswith(ref_id + "-") or name.startswith(ref_id + "_"):
            p = os.path.join(store_dir, name)
            if os.path.isfile(p):
                best = p
    return best


class InstallResolver:
    """安装调度与 bundle 展开。"""

    def __init__(self, mods_root: str | None = None):
        self.mm = get_mod_manager()
        if mods_root:
            self.mods_root = os.path.abspath(mods_root)
        else:
            self.mods_root = self.mm.mods_root

    def install_package_dispatch(
        self,
        package_path: str,
        store_dir: str,
        *,
        verify_signature: bool = True,
        activate: bool = True,
        depth: int = 0,
        rollback_stack: list[tuple[str, str]] | None = None,
    ) -> tuple[bool, str, Any]:
        """
        rollback_stack: 追加 (kind, path) — kind 为 mod_dir|employee_dir，path 为安装目标目录。
        """
        rb = rollback_stack if rollback_stack is not None else []

        try:
            art = peek_artifact(package_path)
        except Exception as e:
            return False, f"无法读取包：{e}", None

        if art == ARTIFACT_EMPLOYEE_PACK:
            reg = get_employee_registry(self.mods_root)
            pack_id = ""
            try:
                from .artifact_package import peek_manifest_from_zip

                pack_id = (peek_manifest_from_zip(package_path).get("id") or "").strip()
            except Exception:
                pass
            ok, msg = reg.install_from_package(package_path, verify_signature=verify_signature)
            if ok and pack_id:
                rb.append(("employee_dir", os.path.join(self.mods_root, "_employees", pack_id)))
            if not ok:
                self._rollback(rb)
            return ok, msg, None

        if art == ARTIFACT_BUNDLE:
            return self._install_bundle_zip(
                package_path,
                store_dir,
                verify_signature=verify_signature,
                activate=activate,
                depth=depth,
                rollback_stack=rb,
            )

        ok, msg, meta = self.mm.install_mod_package(
            package_path,
            verify_signature=verify_signature,
            activate=activate,
        )
        if ok and meta and getattr(meta, "id", None):
            rb.append(("mod_dir", os.path.join(self.mods_root, meta.id)))
        if not ok:
            self._rollback(rb)
        return ok, msg, meta

    def _rollback(self, rb: list[tuple[str, str]]) -> None:
        from .registry import get_mod_registry

        reg = get_mod_registry()
        for kind, path in reversed(rb):
            try:
                if kind == "mod_dir" and path:
                    mid = os.path.basename(path.rstrip("/\\"))
                    if reg.get_mod_metadata(mid):
                        self.mm.unload_mod(mid)
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                elif (
                    kind == "employee_dir"
                    and path
                    and os.path.isdir(path)
                    or path
                    and os.path.exists(path)
                ):
                    shutil.rmtree(path, ignore_errors=True)
                logger.warning("install rollback: removed %s %s", kind, path)
            except Exception as e:
                logger.warning("rollback failed for %s: %s", path, e)
        rb.clear()

    def _install_bundle_zip(
        self,
        package_path: str,
        store_dir: str,
        *,
        verify_signature: bool,
        activate: bool,
        depth: int,
        rollback_stack: list[tuple[str, str]],
    ) -> tuple[bool, str, Any]:
        if depth > BUNDLE_MAX_DEPTH:
            self._rollback(rollback_stack)
            return False, f"bundle 嵌套超过 {BUNDLE_MAX_DEPTH} 层", None
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_root, manifest = ModPackage.extract_package(
                    package_path, temp_dir, verify_signature=verify_signature
                )
                ve = validate_bundle_manifest(manifest, depth=depth)
                if ve:
                    self._rollback(rollback_stack)
                    return False, "; ".join(ve), None
                b = manifest.get("bundle") or {}
                embeds = b.get("embeds") if isinstance(b.get("embeds"), list) else []
                for rel in embeds:
                    rel = str(rel).strip().lstrip("/").replace("/", os.sep)
                    inner = os.path.join(extract_root, rel)
                    if not os.path.isfile(inner):
                        self._rollback(rollback_stack)
                        return False, f"bundle 缺少嵌入文件：{rel}", None
                    ok, msg, meta = self.install_package_dispatch(
                        inner,
                        store_dir,
                        verify_signature=verify_signature,
                        activate=activate,
                        depth=depth + 1,
                        rollback_stack=rollback_stack,
                    )
                    if not ok:
                        self._rollback(rollback_stack)
                        return False, f"安装嵌入失败 ({rel}): {msg}", meta
                contains = b.get("contains") if isinstance(b.get("contains"), list) else []
                for item in contains:
                    if not isinstance(item, dict):
                        continue
                    ref = (item.get("ref") or "").strip()
                    if not ref:
                        continue
                    path = _find_package_in_store(store_dir, ref)
                    if not path:
                        self._rollback(rollback_stack)
                        return False, f"商店目录中未找到 ref={ref} 的包", None
                    ok, msg, meta = self.install_package_dispatch(
                        path,
                        store_dir,
                        verify_signature=verify_signature,
                        activate=activate,
                        depth=depth + 1,
                        rollback_stack=rollback_stack,
                    )
                    if not ok:
                        self._rollback(rollback_stack)
                        return False, f"安装成员失败 (ref={ref}): {msg}", meta
                return True, "bundle 安装完成", None
        except ModSignatureError as e:
            self._rollback(rollback_stack)
            return False, f"签名验证失败：{e}", None
        except ModPackageError as e:
            self._rollback(rollback_stack)
            return False, str(e), None
        except Exception as e:
            logger.exception("bundle install failed")
            self._rollback(rollback_stack)
            return False, str(e), None


def get_install_resolver() -> InstallResolver:
    return InstallResolver()
