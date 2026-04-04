"""
Mod Manager - Core manager for scanning, loading, and managing mods
"""

import importlib
import importlib.util
import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

from .manifest import ModMetadata, parse_manifest, validate_dependencies
from .registry import get_mod_registry

logger = logging.getLogger(__name__)


def is_mods_disabled() -> bool:
    """为 true 时不加载任何 Mod（扩展蓝图、行业覆盖、Hooks 等），仅用核心与原始配置/数据库。"""
    v = (os.environ.get("XCAGI_DISABLE_MODS") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _default_mods_root() -> str:
    """
    解析 mods 根目录。
    源码树：.../XCAGI/app/infrastructure/mods/mod_manager.py -> .../XCAGI/mods
    若包装进 site-packages，上一级不再是项目根，需回退到环境变量或从 cwd 向上查找。
    """
    logger.info(f"[_default_mods_root] Resolving mods root, CWD: {os.getcwd()}")

    env = (os.environ.get("XCAGI_MODS_ROOT") or os.environ.get("XCAGI_MODS_DIR") or "").strip()
    if env:
        p = os.path.abspath(env)
        if os.path.isdir(p):
            logger.info("[_default_mods_root] Mods root from env: %s", p)
            return p
        logger.warning("[_default_mods_root] XCAGI_MODS_ROOT / XCAGI_MODS_DIR is set but not a directory: %s", p)

    file_here = os.path.abspath(__file__)
    from_pkg_layout = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(file_here)))), "mods"
    )
    logger.info(f"[_default_mods_root] Checking package-relative path: {from_pkg_layout}, exists: {os.path.isdir(from_pkg_layout)}")
    if os.path.isdir(from_pkg_layout):
        logger.info("[_default_mods_root] Mods root (next to app package): %s", from_pkg_layout)
        return from_pkg_layout

    cwd_mods = os.path.join(os.getcwd(), "mods")
    logger.info(f"[_default_mods_root] Checking CWD mods: {cwd_mods}, exists: {os.path.isdir(cwd_mods)}")
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
            spec = spec[len("backend."):]
        try:
            module_name, _, attr = spec.rpartition(".")
            if not module_name or not attr:
                logger.error("Invalid hook handler spec for mod %s: %r", mod_id, handler_spec)
                continue
            module = import_mod_backend_py(mod_fs_path, mod_id, module_name)
            handler = getattr(module, attr, None)
            if not callable(handler):
                logger.error(
                    "Hook handler not callable for mod %s: %r", mod_id, handler_spec
                )
                continue
            subscribe(event, handler)
            logger.info("Mod %s hook registered: %s -> %s", mod_id, event, spec)
        except Exception as e:
            logger.error("Failed to register hook %r for mod %s: %s", event, mod_id, e)


def _short_exc_message(exc: BaseException, max_len: int = 480) -> str:
    s = str(exc).strip() or type(exc).__name__
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


class ModManager:
    def __init__(self, mods_root: Optional[str] = None):
        if mods_root is None:
            mods_root = _default_mods_root()
        self.mods_root = mods_root
        self._loaded_mods: List[str] = []
        self._mod_import_cache: dict = {}
        # 最近一次 load_all_mods / load_mod_blueprints 的失败摘要，供 /api/mods/loading-status 展示
        self._recent_load_failures: List[Dict[str, str]] = []
        self._blueprint_failures: List[Dict[str, str]] = []
        self._scan_manifest_errors: List[Dict[str, str]] = []
        # ensure_mods_loaded：注册表为空但磁盘有 manifest 时重复尝试（节流，避免「只试一次」后永久失败）
        self._last_ensure_at: float = 0.0
        self._ensure_attempts: int = 0

    def _refresh_mods_root_if_needed(self) -> None:
        """
        同步 mods_root：优先采用有效的 XCAGI_MODS_ROOT / XCAGI_MODS_DIR；
        若当前路径不存在则重新 _default_mods_root()。
        避免进程早期 import 顺序或 cwd 导致单例锁死在空目录，之后即使用户改环境变量也无法加载。
        """
        env_raw = (os.environ.get("XCAGI_MODS_ROOT") or os.environ.get("XCAGI_MODS_DIR") or "").strip()
        if env_raw:
            p = os.path.abspath(env_raw)
            if os.path.isdir(p):
                if self.mods_root != p:
                    logger.info("[ModManager] Updating mods_root from env: %s -> %s", self.mods_root, p)
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

    def get_recent_load_failures(self) -> List[Dict[str, str]]:
        return list(self._recent_load_failures)

    def get_blueprint_failures(self) -> List[Dict[str, str]]:
        return list(self._blueprint_failures)

    def get_scan_manifest_errors(self) -> List[Dict[str, str]]:
        return list(self._scan_manifest_errors)

    def ensure_mods_loaded(self, app: Any) -> None:
        """若注册表中尚无 Mod，但 mods 目录下存在合法 manifest，则再执行 load_all_mods + load_mod_blueprints。"""
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
            load_mod_blueprints(app, self)
        except Exception as e:
            # 避免扫描/加载异常导致 /api/mods、/api/mods/routes 等整段 500，前端 Mod 列表与路由永久拉取失败
            logger.exception(
                "[ModManager] ensure_mods_loaded failed (mods_root=%s): %s",
                getattr(self, "mods_root", None),
                e,
            )

    def scan_mods(self) -> List[ModMetadata]:
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
            mod_path = os.path.join(self.mods_root, entry)
            if not os.path.isdir(mod_path):
                continue

            manifest_path = os.path.join(mod_path, "manifest.json")
            logger.info(f"[ModManager] Checking mod entry: {entry}, manifest exists: {os.path.isfile(manifest_path)}")

            metadata = parse_manifest(mod_path)
            if metadata:
                mods.append(metadata)
                logger.info(f"[ModManager] Found mod: {metadata.id} ({metadata.name}) v{metadata.version}")
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

        logger.info(f"[ModManager] Mod metadata parsed: id={metadata.id}, name={metadata.name}, version={metadata.version}")

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

        if instance and hasattr(instance, 'cleanup'):
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

    def get_mod(self, mod_id: str) -> Optional[ModMetadata]:
        registry = get_mod_registry()
        return registry.get_mod_metadata(mod_id)

    def list_loaded_mods(self) -> List[ModMetadata]:
        registry = get_mod_registry()
        return registry.list_mods()

    def load_all_mods(self) -> List[str]:
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
                    logger.warning(f"[ModManager] Skipping mod {metadata.id} due to unsatisfied dependencies")
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


_mod_manager: Optional[ModManager] = None


def get_mod_manager() -> ModManager:
    global _mod_manager
    if _mod_manager is None:
        _mod_manager = ModManager()
    return _mod_manager


def load_mod_blueprints(app, mod_manager: Optional[ModManager] = None) -> None:
    if mod_manager is None:
        mod_manager = get_mod_manager()

    mod_manager._blueprint_failures = []
    registry = get_mod_registry()

    for mod_id in mod_manager._loaded_mods:
        metadata = registry.get_mod_metadata(mod_id)
        if not metadata or not metadata.backend_entry:
            continue

        try:
            # Flask 以 Blueprint 名为键；各 Mod 的 create_blueprint(mod_id) 与 manifest id 一致
            if mod_id in getattr(app, "blueprints", {}):
                logger.info("Blueprint for mod %s already registered on app, skip", mod_id)
                continue
            mod_fs_path = metadata.mod_path
            if not mod_fs_path:
                logger.error("Mod %s missing mod_path; skip blueprint registration", mod_id)
                mod_manager.record_blueprint_failure(mod_id, "manifest 缺少 mod_path，无法注册蓝图")
                continue
            module = import_mod_backend_py(mod_fs_path, mod_id, metadata.backend_entry)
            if hasattr(module, 'register_blueprints'):
                register_fn = getattr(module, 'register_blueprints')
                if callable(register_fn):
                    register_fn(app, mod_id)
                    logger.info(f"Blueprints registered for mod: {mod_id}")
        except Exception as e:
            logger.error(f"Failed to register blueprints for {mod_id}: {e}", exc_info=True)
            mod_manager.record_blueprint_failure(mod_id, _short_exc_message(e))