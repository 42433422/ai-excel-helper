"""
Mod Manager - Core manager for scanning, loading, and managing mods
"""

import importlib
import importlib.util
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import zipfile
from typing import Any

from .artifact_constants import ARTIFACT_BUNDLE, ARTIFACT_EMPLOYEE_PACK, normalize_artifact
from .artifact_package import (
    validate_bundle_manifest,
    validate_employee_pack_manifest,
)
from .manifest import ModMetadata, parse_manifest, validate_dependencies
from .package import ModPackage, ModPackageError, ModSignatureError
from .registry import get_mod_registry

logger = logging.getLogger(__name__)


def is_mods_disabled() -> bool:
    """为 true 时不加载任何 Mod（扩展蓝图、行业覆盖、Hooks 等），仅用核心与原始配置/数据库。"""
    v = (os.environ.get("XCAGI_DISABLE_MODS") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _default_mods_root() -> str:
    """
    解析 mods 根目录。
    源码树：app/infrastructure/mods/mod_manager.py；默认 mods 目录为 XCAGI/mods（由 run.py 设置 XCAGI_MODS_ROOT）
    若包装进 site-packages，上一级不再是项目根，需回退到环境变量或从 cwd 向上查找。
    """
    logger.info(f"[_default_mods_root] Resolving mods root, CWD: {os.getcwd()}")

    env = (os.environ.get("XCAGI_MODS_ROOT") or os.environ.get("XCAGI_MODS_DIR") or "").strip()
    if env:
        p = os.path.abspath(env)
        if os.path.isdir(p):
            logger.info("[_default_mods_root] Mods root from env: %s", p)
            return p
        logger.warning(
            "[_default_mods_root] XCAGI_MODS_ROOT / XCAGI_MODS_DIR is set but not a directory: %s",
            p,
        )

    file_here = os.path.abspath(__file__)
    from_pkg_layout = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(file_here)))), "mods"
    )
    logger.info(
        f"[_default_mods_root] Checking package-relative path: {from_pkg_layout}, exists: {os.path.isdir(from_pkg_layout)}"
    )
    if os.path.isdir(from_pkg_layout):
        logger.info("[_default_mods_root] Mods root (next to app package): %s", from_pkg_layout)
        return from_pkg_layout

    cwd_mods = os.path.join(os.getcwd(), "mods")
    logger.info(
        f"[_default_mods_root] Checking CWD mods: {cwd_mods}, exists: {os.path.isdir(cwd_mods)}"
    )
    if os.path.isdir(cwd_mods):
        logger.info("[_default_mods_root] Mods root (./mods from cwd): %s", cwd_mods)
        return cwd_mods

    cur = os.path.abspath(os.getcwd())
    for i in range(8):
        trial = os.path.join(cur, "mods")
        logger.info(f"[_default_mods_root] Walking up: {trial}, exists: {os.path.isdir(trial)}")
        if os.path.isdir(trial):
            logger.info("[_default_mods_root] Mods root (walk up from cwd): %s", trial)
            return trial
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    logger.warning(
        "[_default_mods_root] No mods directory found; using package-relative path (may be empty): %s. "
        "Set XCAGI_MODS_ROOT or run from project root.",
        from_pkg_layout,
    )
    return from_pkg_layout


def _backend_path_for_mod(mod_path: str) -> str:
    return os.path.join(mod_path, "backend")


def import_mod_backend_py(mod_path: str, mod_id: str, stem: str):
    """
    从指定 Mod 的 backend/<stem>.py 按文件路径加载为唯一模块名，避免多个 Mod 都叫 blueprints/services 时 sys.modules 冲突。
    stem 不含 .py，且仅支持 backend 根目录下单文件（非子包）。
    """
    backend_path = _backend_path_for_mod(mod_path)
    path = os.path.join(backend_path, f"{stem}.py")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Mod {mod_id} backend file missing: {path}")
    safe = "".join(c if c.isalnum() else "_" for c in mod_id)
    spec_name = f"_xcagi_mod_{safe}_{stem}"
    existing = sys.modules.get(spec_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(spec_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec_name] = module
    spec.loader.exec_module(module)
    return module


def _register_mod_hooks(mod_id: str, metadata: ModMetadata) -> None:
    """Subscribe manifest hook handlers. Paths are relative to each mod's backend/ on sys.path."""
    if not metadata.hooks:
        return
    from app.infrastructure.mods.hooks import subscribe

    mod_fs_path = metadata.mod_path or ""
    if not mod_fs_path:
        logger.error("Mod %s has no mod_path; cannot resolve hook handlers", mod_id)
        return

    for event, handler_spec in metadata.hooks.items():
        spec = (handler_spec or "").strip()
        if spec.startswith("backend."):
            spec = spec[len("backend.") :]
        try:
            module_name, _, attr = spec.rpartition(".")
            if not module_name or not attr:
                logger.error("Invalid hook handler spec for mod %s: %r", mod_id, handler_spec)
                continue
            module = import_mod_backend_py(mod_fs_path, mod_id, module_name)
            handler = getattr(module, attr, None)
            if not callable(handler):
                logger.error("Hook handler not callable for mod %s: %r", mod_id, handler_spec)
                continue
            subscribe(event, handler)
            logger.info("Mod %s hook registered: %s -> %s", mod_id, event, spec)
        except Exception as e:
            logger.error("Failed to register hook %r for mod %s: %s", event, mod_id, e)


def _short_exc_message(exc: BaseException, max_len: int = 480) -> str:
    s = str(exc).strip() or type(exc).__name__
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


class ModManager:
    def __init__(self, mods_root: str | None = None):
        if mods_root is None:
            mods_root = _default_mods_root()
        self.mods_root = mods_root
        self._loaded_mods: list[str] = []
        self._mod_import_cache: dict = {}
        # 最近一次 load_all_mods / load_mod_routes 的失败摘要，供 /api/mods/loading-status 展示
        self._recent_load_failures: list[dict[str, str]] = []
        self._blueprint_failures: list[dict[str, str]] = []
        self._scan_manifest_errors: list[dict[str, str]] = []
        # ensure_mods_loaded：注册表为空但磁盘有 manifest 时重复尝试（节流，避免「只试一次」后永久失败）
        self._last_ensure_at: float = 0.0
        self._ensure_attempts: int = 0

    def _refresh_mods_root_if_needed(self) -> None:
        """
        同步 mods_root：优先采用有效的 XCAGI_MODS_ROOT / XCAGI_MODS_DIR；
        若当前路径不存在则重新 _default_mods_root()。
        避免进程早期 import 顺序或 cwd 导致单例锁死在空目录，之后即使用户改环境变量也无法加载。
        """
        env_raw = (
            os.environ.get("XCAGI_MODS_ROOT") or os.environ.get("XCAGI_MODS_DIR") or ""
        ).strip()
        if env_raw:
            p = os.path.abspath(env_raw)
            if os.path.isdir(p):
                if self.mods_root != p:
                    logger.info(
                        "[ModManager] Updating mods_root from env: %s -> %s", self.mods_root, p
                    )
                    self.mods_root = p
                    self._ensure_attempts = 0
                return
            logger.warning(
                "[ModManager] XCAGI_MODS_ROOT / XCAGI_MODS_DIR is set but not a directory: %s (keeping %s)",
                p,
                self.mods_root,
            )
        if not os.path.isdir(self.mods_root):
            fb = _default_mods_root()
            if fb != self.mods_root:
                logger.warning(
                    "[ModManager] mods_root was missing or invalid (%s), re-resolved -> %s",
                    self.mods_root,
                    fb,
                )
                self.mods_root = fb
                self._ensure_attempts = 0

    def _record_load_failure(self, mod_id: str, stage: str, message: str) -> None:
        self._recent_load_failures.append(
            {"mod_id": mod_id, "stage": stage, "message": message[:500]}
        )

    def record_blueprint_failure(self, mod_id: str, message: str) -> None:
        self._blueprint_failures.append({"mod_id": mod_id, "message": message[:500]})

    def get_recent_load_failures(self) -> list[dict[str, str]]:
        return list(self._recent_load_failures)

    def get_blueprint_failures(self) -> list[dict[str, str]]:
        return list(self._blueprint_failures)

    def get_scan_manifest_errors(self) -> list[dict[str, str]]:
        return list(self._scan_manifest_errors)

    def ensure_mods_loaded(self, app: Any) -> None:
        """若注册表中尚无 Mod，但 mods 目录下存在合法 manifest，则再执行 load_all_mods + load_mod_routes。"""
        try:
            if is_mods_disabled():
                return
            self._refresh_mods_root_if_needed()
            if self.list_loaded_mods():
                return
            discovered = self.scan_mods()
            if not discovered:
                return
            now = time.monotonic()
            if self._last_ensure_at and (now - self._last_ensure_at) < 1.5:
                return
            if self._ensure_attempts >= 20:
                return
            self._last_ensure_at = now
            self._ensure_attempts += 1
            logger.warning(
                "[ModManager] 注册表无 Mod 但磁盘有 manifest，第 %s 次尝试加载：mods_root=%s，manifest 数=%s",
                self._ensure_attempts,
                self.mods_root,
                len(discovered),
            )
            self.load_all_mods()
            load_mod_routes(app, self)
        except Exception as e:
            # 避免扫描/加载异常导致 /api/mods、/api/mods/routes 等整段 500，前端 Mod 列表与路由永久拉取失败
            logger.exception(
                "[ModManager] ensure_mods_loaded failed (mods_root=%s): %s",
                getattr(self, "mods_root", None),
                e,
            )

    def scan_mods(self) -> list[ModMetadata]:
        self._refresh_mods_root_if_needed()
        logger.info(f"[ModManager] Scanning mods directory: {self.mods_root}")
        logger.info(f"[ModManager] CWD: {os.getcwd()}")
        logger.info(f"[ModManager] __file__: {os.path.abspath(__file__)}")

        self._scan_manifest_errors = []

        if not os.path.isdir(self.mods_root):
            logger.warning(f"[ModManager] Mods directory does not exist: {self.mods_root}")
            return []

        mods = []
        for entry in os.listdir(self.mods_root):
            if entry.startswith("_"):
                continue
            mod_path = os.path.join(self.mods_root, entry)
            if not os.path.isdir(mod_path):
                continue

            manifest_path = os.path.join(mod_path, "manifest.json")
            logger.info(
                f"[ModManager] Checking mod entry: {entry}, manifest exists: {os.path.isfile(manifest_path)}"
            )

            metadata = parse_manifest(mod_path)
            if metadata:
                mods.append(metadata)
                logger.info(
                    f"[ModManager] Found mod: {metadata.id} ({metadata.name}) v{metadata.version}"
                )
            else:
                logger.warning(f"[ModManager] Failed to parse manifest for mod entry: {entry}")
                self._scan_manifest_errors.append(
                    {
                        "entry": entry,
                        "message": "manifest.json 缺失或无法解析（检查 JSON 与必填字段 id）",
                    }
                )

        logger.info(f"[ModManager] Total mods found: {len(mods)}")
        return mods

    def load_mod(self, mod_id: str) -> bool:
        registry = get_mod_registry()

        logger.info(f"[ModManager] Attempting to load mod: {mod_id}")

        if registry.get_mod_metadata(mod_id):
            logger.info(f"[ModManager] Mod {mod_id} is already loaded")
            # 与 load_mod_routes 对齐：历史上偶发「注册表已有元数据但 _loaded_mods 漏记」，
            # 会导致该 Mod 的 /api/mod/<id>/... 永远不挂载（仅命中 SPA 兜底 404）。
            if mod_id not in self._loaded_mods:
                logger.warning(
                    "[ModManager] Mod %s in registry but missing from _loaded_mods; syncing list",
                    mod_id,
                )
                self._loaded_mods.append(mod_id)
            return True

        mod_path = os.path.join(self.mods_root, mod_id)
        logger.info(f"[ModManager] Mod path: {mod_path}")
        if not os.path.isdir(mod_path):
            logger.error(f"[ModManager] Mod directory not found: {mod_path}")
            self._record_load_failure(mod_id, "fs", f"目录不存在: {mod_path}")
            return False

        metadata = parse_manifest(mod_path)
        if not metadata:
            logger.error(f"[ModManager] Failed to parse manifest for mod: {mod_id}")
            self._record_load_failure(mod_id, "manifest", "manifest.json 无效或缺少 id")
            return False

        logger.info(
            f"[ModManager] Mod metadata parsed: id={metadata.id}, name={metadata.name}, version={metadata.version}"
        )

        if normalize_artifact({"artifact": metadata.artifact}) == ARTIFACT_BUNDLE:
            if registry.get_mod_metadata(mod_id):
                return True
            if registry.register_mod(metadata):
                self._loaded_mods.append(mod_id)
                logger.info("[ModManager] Registered bundle metadata only (no backend): %s", mod_id)
                return True
            logger.warning("[ModManager] Bundle %s register_mod returned False", mod_id)
            return True

        deps = registry.list_mod_ids()
        logger.info(f"[ModManager] Current loaded mods for dependency check: {deps}")
        if not validate_dependencies(metadata, deps):
            logger.warning(f"[ModManager] Dependencies not satisfied for mod: {mod_id}")
            self._record_load_failure(
                mod_id,
                "dependencies",
                "依赖未满足（需先加载所依赖的 mod，或检查 manifest dependencies）",
            )
            return False

        try:
            self._load_mod_backend(mod_id, mod_path, metadata)
            registry.register_mod(metadata)
            self._loaded_mods.append(mod_id)
            logger.info(f"[ModManager] Mod loaded successfully: {mod_id}")
            return True
        except Exception as e:
            logger.error(f"[ModManager] Failed to load mod {mod_id}: {e}", exc_info=True)
            self._record_load_failure(mod_id, "backend", _short_exc_message(e))
            return False

    def _load_mod_backend(self, mod_id: str, mod_path: str, metadata: ModMetadata):
        backend_path = os.path.join(mod_path, "backend")
        if not os.path.isdir(backend_path):
            logger.debug(f"No backend directory for mod: {mod_id}")
            return

        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        if metadata.backend_entry:
            try:
                module = import_mod_backend_py(mod_path, mod_id, metadata.backend_entry)
                if hasattr(module, metadata.backend_init):
                    init_fn = getattr(module, metadata.backend_init)
                    if callable(init_fn):
                        init_fn()
            except Exception as e:
                logger.error(
                    f"Failed to load backend entry for {mod_id}: {e}",
                    exc_info=True,
                )
                raise

        _register_mod_hooks(mod_id, metadata)

    def unload_mod(self, mod_id: str) -> bool:
        registry = get_mod_registry()
        instance = registry.get_mod_instance(mod_id)

        if instance and hasattr(instance, "cleanup"):
            try:
                instance.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up mod {mod_id}: {e}")

        registry.unregister_mod(mod_id)
        if mod_id in self._loaded_mods:
            self._loaded_mods.remove(mod_id)

        try:
            from app.infrastructure.mods.comms import get_mod_comms

            get_mod_comms().unregister_all(mod_id)
        except Exception as e:
            logger.warning("Mod comms cleanup failed for %s: %s", mod_id, e)

        logger.info(f"Mod unloaded: {mod_id}")
        return True

    def install_mod_package(
        self,
        package_path: str,
        verify_signature: bool = True,
        activate: bool = True,
    ) -> tuple[bool, str, ModMetadata | None]:
        """
        安装 MOD 包

        Args:
            package_path: .xcmod 文件路径
            verify_signature: 是否验证签名
            activate: 安装后是否立即激活

        Returns:
            (成功标志，消息，元数据)
        """
        try:
            self._refresh_mods_root_if_needed()
            os.makedirs(self.mods_root, exist_ok=True)

            logger.info(f"Installing MOD package: {package_path}")

            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    extract_path, manifest = ModPackage.extract_package(
                        package_path, temp_dir, verify_signature=verify_signature
                    )
                except ModSignatureError as e:
                    return False, f"签名验证失败：{e}", None
                except ModPackageError as e:
                    return False, f"MOD 包无效：{e}", None

                mod_id = manifest.get("id", "")
                if not mod_id:
                    return False, "MOD 包缺少 id 字段", None

                target_path = os.path.join(self.mods_root, mod_id)

                if os.path.exists(target_path):
                    existing_metadata = parse_manifest(target_path)
                    existing_version = existing_metadata.version if existing_metadata else "unknown"
                    new_version = manifest.get("version", "unknown")
                    logger.info(
                        f"MOD {mod_id} already exists (v{existing_version}), updating to v{new_version}"
                    )
                    shutil.rmtree(target_path)

                shutil.copytree(extract_path, target_path)
                logger.info(f"MOD installed to: {target_path}")

                if activate:
                    if self.load_mod(mod_id):
                        metadata = parse_manifest(target_path)
                        return True, f"MOD {mod_id} 安装成功", metadata
                    else:
                        return False, f"MOD {mod_id} 安装成功但加载失败", None
                else:
                    metadata = parse_manifest(target_path)
                    return True, f"MOD {mod_id} 安装成功（未激活）", metadata

        except Exception as e:
            logger.exception("MOD installation failed")
            return False, f"安装失败：{e}", None

    def uninstall_mod(self, mod_id: str, remove_files: bool = True) -> tuple[bool, str]:
        """
        卸载 MOD

        Args:
            mod_id: MOD ID
            remove_files: 是否删除文件

        Returns:
            (成功标志，消息)
        """
        try:
            registry = get_mod_registry()
            metadata = registry.get_mod_metadata(mod_id)

            if not metadata:
                from .employee_registry import get_employee_registry

                er = get_employee_registry(self.mods_root)
                emp_path = os.path.join(er._root(), mod_id)
                if os.path.isdir(emp_path):
                    ok, msg = er.uninstall_pack(mod_id, remove_files=remove_files)
                    return ok, msg
                return False, f"MOD {mod_id} 未加载或不存在"

            logger.info(f"Uninstalling MOD: {mod_id}")

            if mod_id in self._loaded_mods:
                self.unload_mod(mod_id)

            if remove_files:
                mod_path = os.path.join(self.mods_root, mod_id)
                if os.path.exists(mod_path):
                    shutil.rmtree(mod_path)
                    logger.info(f"MOD files removed: {mod_path}")

            return True, f"MOD {mod_id} 卸载成功"

        except Exception as e:
            logger.exception("MOD uninstallation failed")
            return False, f"卸载失败：{e}"

    def update_mod(
        self,
        mod_id: str,
        package_path: str,
        verify_signature: bool = True,
    ) -> tuple[bool, str, ModMetadata | None]:
        """
        更新 MOD

        Args:
            mod_id: MOD ID
            package_path: .xcmod 文件路径
            verify_signature: 是否验证签名

        Returns:
            (成功标志，消息，元数据)
        """
        try:
            registry = get_mod_registry()
            current_metadata = registry.get_mod_metadata(mod_id)

            if not current_metadata:
                return False, f"MOD {mod_id} 未安装，请先安装", None

            new_package = ModPackage(package_path)
            new_manifest = new_package.manifest

            current_version = current_metadata.version
            new_version = new_manifest.get("version", "unknown")

            logger.info(f"Updating MOD {mod_id}: v{current_version} -> v{new_version}")

            was_loaded = mod_id in self._loaded_mods

            if was_loaded:
                self.unload_mod(mod_id)

            mod_path = os.path.join(self.mods_root, mod_id)
            if os.path.exists(mod_path):
                shutil.rmtree(mod_path)

            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    extract_path, _ = ModPackage.extract_package(
                        package_path, temp_dir, verify_signature=verify_signature
                    )
                    shutil.copytree(extract_path, mod_path)
                except Exception as e:
                    logger.error(f"Failed to extract package: {e}")
                    if was_loaded:
                        self.load_mod(mod_id)
                    return False, f"更新失败：{e}", None

            if was_loaded:
                if self.load_mod(mod_id):
                    metadata = parse_manifest(mod_path)
                    return True, f"MOD {mod_id} 更新成功 (v{new_version})", metadata
                else:
                    return False, "MOD 更新成功但加载失败", None
            else:
                metadata = parse_manifest(mod_path)
                return True, f"MOD {mod_id} 更新成功 (v{new_version})", metadata

        except Exception as e:
            logger.exception("MOD update failed")
            return False, f"更新失败：{e}", None

    def validate_mod_package(self, package_path: str) -> tuple[bool, str, dict[str, Any]]:
        """
        验证 MOD 包

        Args:
            package_path: .xcmod 文件路径

        Returns:
            (有效标志，消息，详细信息)
        """
        try:
            if not os.path.isfile(package_path):
                return False, "文件不存在", {}

            if not zipfile.is_zipfile(package_path):
                return False, "不是有效的 ZIP 文件", {}

            with tempfile.TemporaryDirectory() as temp_dir:
                extract_path, manifest = ModPackage.extract_package(
                    package_path, temp_dir, verify_signature=False
                )

                mod_id = manifest.get("id", "")
                version = manifest.get("version", "")

                if not mod_id:
                    return False, "缺少必填字段 'id'", {}

                errors: list[str] = []
                warnings: list[str] = []

                required_fields = ["id", "name", "version"]
                for field in required_fields:
                    if not manifest.get(field):
                        errors.append(f"缺少必填字段：{field}")

                art = normalize_artifact(manifest)
                if art == ARTIFACT_BUNDLE:
                    errors.extend(validate_bundle_manifest(manifest, depth=0))
                elif art == ARTIFACT_EMPLOYEE_PACK:
                    errors.extend(validate_employee_pack_manifest(manifest))
                else:
                    backend_path = os.path.join(extract_path, "backend")
                    if os.path.isdir(backend_path):
                        backend_entry = manifest.get("backend", {}).get("entry", "")
                        if backend_entry:
                            entry_file = os.path.join(backend_path, f"{backend_entry}.py")
                            if not os.path.isfile(entry_file):
                                errors.append(f"后端入口文件不存在：{backend_entry}.py")

                    frontend_path = os.path.join(extract_path, "frontend")
                    if os.path.isdir(frontend_path):
                        frontend_routes = manifest.get("frontend", {}).get("routes", "")
                        if frontend_routes:
                            routes_file = os.path.join(frontend_path, f"{frontend_routes}.js")
                            if not os.path.isfile(routes_file):
                                errors.append(f"前端路由文件不存在：{frontend_routes}.js")

                is_valid = len(errors) == 0

                return (
                    is_valid,
                    "验证通过" if is_valid else "; ".join(errors),
                    {
                        "id": mod_id,
                        "name": manifest.get("name", ""),
                        "version": version,
                        "author": manifest.get("author", ""),
                        "artifact": art,
                        "errors": errors,
                        "warnings": warnings,
                    },
                )

        except ModPackageError as e:
            return False, str(e), {}
        except Exception as e:
            logger.exception("MOD validation failed")
            return False, f"验证失败：{e}", {}

    def get_mod(self, mod_id: str) -> ModMetadata | None:
        registry = get_mod_registry()
        return registry.get_mod_metadata(mod_id)

    def list_loaded_mods(self) -> list[ModMetadata]:
        registry = get_mod_registry()
        return registry.list_mods()

    @staticmethod
    def _metadata_to_api_dict(m: ModMetadata) -> dict[str, Any]:
        """与前端 /api/mods/ 列表项、侧栏 manifest 展示字段对齐。"""
        art = normalize_artifact({"artifact": m.artifact})
        row: dict[str, Any] = {
            "id": m.id,
            "name": m.name,
            "version": m.version,
            "author": m.author or "",
            "description": m.description or "",
            "primary": bool(m.primary),
            "artifact": art,
            "menu": list(m.frontend_menu) if m.frontend_menu else [],
            "menu_overrides": list(m.frontend_menu_overrides) if m.frontend_menu_overrides else [],
            "workflow_employees": list(m.workflow_employees) if m.workflow_employees else [],
            "comms_exports": list(m.comms_exports) if m.comms_exports else [],
        }
        if art == ARTIFACT_BUNDLE:
            row["type"] = "bundle"
        return row

    def list_mods(self) -> list[dict[str, Any]]:
        """
        已加载 Mod 元数据优先；否则回退磁盘扫描 manifest。
        供 GET /api/mods/、Neuro SAFETY_MODS_LIST 使用（前端读 result.data[]）。
        """
        if is_mods_disabled():
            return []
        self._refresh_mods_root_if_needed()
        loaded = self.list_loaded_mods()
        if loaded:
            rows = [self._metadata_to_api_dict(x) for x in loaded]
        else:
            rows = [self._metadata_to_api_dict(x) for x in self.scan_mods()]
        try:
            from .employee_registry import get_employee_registry

            rows = rows + get_employee_registry(self.mods_root).list_for_mods_api()
        except Exception as e:
            logger.warning("employee registry merge skipped: %s", e)
        return rows

    def list_all_mods(self) -> list[dict[str, Any]]:
        """
        始终返回磁盘扫描的全部 Mod 列表，不受已加载状态影响。
        供 GET /api/mods/?all=1 使用，返回所有可选的标准扩展包。
        """
        if is_mods_disabled():
            return []
        self._refresh_mods_root_if_needed()
        # 直接扫描磁盘，不依赖已加载状态
        rows = [self._metadata_to_api_dict(x) for x in self.scan_mods()]
        try:
            from .employee_registry import get_employee_registry

            rows = rows + get_employee_registry(self.mods_root).list_for_mods_api()
        except Exception as e:
            logger.warning("employee registry merge skipped: %s", e)
        return rows

    def get_routes(self) -> list[dict[str, str]]:
        """
        返回含 mod_id 的条目，供前端 registerModRoutes 匹配 Vite glob。
        manifest frontend.routes 非空即视为存在 frontend/routes.js（或约定路径）。
        """
        if is_mods_disabled():
            return []
        self._refresh_mods_root_if_needed()
        out: list[dict[str, str]] = []
        for m in self.scan_mods():
            rp = (m.frontend_routes or "").strip()
            if rp:
                out.append({"mod_id": m.id, "routes_path": rp})
        return out

    def load_all_mods(self) -> list[str]:
        self._recent_load_failures = []
        self._blueprint_failures = []
        mods = self.scan_mods()
        # primary Mod 先加载，便于后续依赖其它 Mod 的声明顺序（当前主要影响日志与排查顺序）
        mods.sort(key=lambda m: (not m.primary, (m.id or "").lower()))
        logger.info(f"[ModManager] load_all_mods: scanned {len(mods)} mods")
        loaded = []

        for metadata in mods:
            logger.info(f"[ModManager] Checking dependencies for mod: {metadata.id}")
            if metadata.dependencies:
                deps_satisfied = validate_dependencies(metadata, loaded)
                if not deps_satisfied:
                    logger.warning(
                        f"[ModManager] Skipping mod {metadata.id} due to unsatisfied dependencies"
                    )
                    self._record_load_failure(
                        metadata.id,
                        "dependencies",
                        "load_all 阶段依赖未满足（可能需先加载其他 mod）",
                    )
                    continue

            if self.load_mod(metadata.id):
                loaded.append(metadata.id)
                logger.info(f"[ModManager] Successfully loaded mod: {metadata.id}")
            else:
                logger.warning(f"[ModManager] Failed to load mod: {metadata.id}")

        logger.info(f"[ModManager] load_all_mods result: {loaded}")
        return loaded


_mod_manager: ModManager | None = None


def get_mod_manager() -> ModManager:
    global _mod_manager
    if _mod_manager is None:
        _mod_manager = ModManager()
    return _mod_manager


def _move_history_fallback_to_end(app) -> None:
    """
    Vue history fallback 在 create_fastapi_app 同步阶段就注册到 app.router.routes 末尾；
    而 Mod 路由在 lifespan 启动事件中通过 include_router 追加（位于 fallback 之后），
    Starlette 按注册顺序匹配，会导致 /api/mod/<id>/... 被 /{fallback:path} 截胡并返回
    `{"success": false, "message": "资源不存在：/api/mod/..."}`。

    注册 Mod 路由后调用本函数：把路径为 "/{fallback:path}" 的 catch-all 路由挪到末尾，
    保证更具体的 Mod 路由先于兜底命中。
    """
    try:
        routes = getattr(getattr(app, "router", None), "routes", None)
        if not isinstance(routes, list) or not routes:
            return
        fallback_path = "/{fallback:path}"
        fallback_routes = [r for r in routes if getattr(r, "path", None) == fallback_path]
        if not fallback_routes:
            return
        for r in fallback_routes:
            try:
                routes.remove(r)
            except ValueError:
                continue
            routes.append(r)
        logger.info(
            "Reordered %d Vue history fallback route(s) to end of app.router.routes",
            len(fallback_routes),
        )
    except Exception as e:
        logger.warning("Failed to reorder history fallback routes: %s", e)


def load_employee_pack_routes(app, mod_manager: ModManager | None = None) -> None:
    """为 ``mods/_employees/<pack_id>/`` 中带 ``backend.entry`` 的 employee_pack 挂载 FastAPI 路由。

    扫描目录不经过 ``scan_mods``（其忽略 ``_`` 前缀），故在此单独注册。
    """
    if mod_manager is None:
        mod_manager = get_mod_manager()
    if is_mods_disabled():
        return
    root = mod_manager.mods_root
    emp_root = os.path.join(root, "_employees")
    if not os.path.isdir(emp_root):
        return
    for name in sorted(os.listdir(emp_root)):
        pack_path = os.path.join(emp_root, name)
        if not os.path.isdir(pack_path):
            continue
        mf = os.path.join(pack_path, "manifest.json")
        if not os.path.isfile(mf):
            continue
        try:
            with open(mf, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if normalize_artifact(data) != ARTIFACT_EMPLOYEE_PACK:
            continue
        backend = data.get("backend") or {}
        entry = str(backend.get("entry") or "").strip()
        if not entry:
            continue
        pack_id = str(data.get("id") or name).strip()
        if not pack_id:
            continue
        try:
            module = import_mod_backend_py(pack_path, pack_id, entry)
            reg = getattr(module, "register_fastapi_routes", None)
            if callable(reg):
                reg(app, pack_id)
                logger.info("FastAPI routes registered for employee_pack: %s", pack_id)
        except Exception as e:
            logger.error("employee_pack route registration failed %s: %s", pack_id, e, exc_info=True)
            mod_manager.record_blueprint_failure(pack_id, str(e)[:500])


def load_mod_routes(app, mod_manager: ModManager | None = None) -> None:
    """加载 Mod 路由到 FastAPI 应用"""
    if mod_manager is None:
        mod_manager = get_mod_manager()

    mod_manager._blueprint_failures = []
    registry = get_mod_registry()

    # 以注册表为准挂载 HTTP 路由：仅依赖 _loaded_mods 时，若列表与「已成功 load_mod 并 register」的
    # 集合不一致，会出现 OpenAPI 里缺少部分 /api/mod/<id>/hello、浏览器 404 的情况。
    routable: list[str] = []
    seen_ids: set[str] = set()
    for meta in registry.list_mods():
        mid = (meta.id or "").strip()
        if not mid or not (meta.backend_entry or "").strip():
            continue
        if mid in seen_ids:
            continue
        seen_ids.add(mid)
        routable.append(mid)
    # 优先保持 load_all_mods 时的顺序（primary 优先等），再补上注册表里有但 _loaded_mods 漏掉的 id
    ordered_ids: list[str] = []
    seen2: set[str] = set()
    for mid in mod_manager._loaded_mods:
        if mid in seen2 or mid not in seen_ids:
            continue
        ordered_ids.append(mid)
        seen2.add(mid)
    for mid in routable:
        if mid not in seen2:
            ordered_ids.append(mid)
            seen2.add(mid)

    for mod_id in ordered_ids:
        metadata = registry.get_mod_metadata(mod_id)
        if not metadata or not metadata.backend_entry:
            continue

        try:
            mod_fs_path = metadata.mod_path
            if not mod_fs_path:
                logger.error("Mod %s missing mod_path; skip route registration", mod_id)
                mod_manager.record_blueprint_failure(mod_id, "manifest 缺少 mod_path，无法注册路由")
                continue
            module = import_mod_backend_py(mod_fs_path, mod_id, metadata.backend_entry)
            registered = False

            # Preferred: native FastAPI route registration.
            if hasattr(module, "register_fastapi_routes"):
                register_fastapi_fn = module.register_fastapi_routes
                if callable(register_fastapi_fn):
                    register_fastapi_fn(app, mod_id)
                    logger.info(f"FastAPI routes registered for mod: {mod_id}")
                    registered = True

            # Optional websocket hook for FastAPI mods.
            if hasattr(module, "register_websocket_routes"):
                ws_register_fn = module.register_websocket_routes
                if callable(ws_register_fn):
                    ws_result = ws_register_fn(app)
                    if ws_result is False:
                        logger.warning("WebSocket routes not registered for mod: %s", mod_id)
                    else:
                        logger.info(f"WebSocket routes registered for mod: {mod_id}")

            if not registered:
                logger.info("Mod %s has no HTTP route registrar, skip", mod_id)
        except Exception as e:
            logger.error(f"Failed to register routes for {mod_id}: {e}", exc_info=True)
            mod_manager.record_blueprint_failure(mod_id, _short_exc_message(e))

    load_employee_pack_routes(app, mod_manager)
    _move_history_fallback_to_end(app)


def load_mod_blueprints(app, mod_manager: ModManager | None = None) -> None:
    """
    历史钩子名（兼容旧 Mod 文档/清单）。

    Mod 的 HTTP 面由 FastAPI ``load_mod_routes`` 注册；此函数为 no-op，避免重复挂载。
    """
    logger.info("load_mod_blueprints: skipped (Mod routes use FastAPI load_mod_routes on main app)")
