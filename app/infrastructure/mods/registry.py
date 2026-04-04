"""
Mod Registry - Singleton registry for loaded mods
"""

import logging
from typing import Dict, List, Optional

from .manifest import ModMetadata

logger = logging.getLogger(__name__)


class ModRegistry:
    _instance: Optional["ModRegistry"] = None

    def __init__(self):
        self._mods: Dict[str, ModMetadata] = {}
        self._mod_instances: Dict[str, object] = {}

    @classmethod
    def get_instance(cls) -> "ModRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_mod(self, metadata: ModMetadata) -> bool:
        if metadata.id in self._mods:
            logger.warning(f"Mod {metadata.id} is already registered")
            return False

        self._mods[metadata.id] = metadata
        logger.info(f"Mod registered: {metadata.id} v{metadata.version}")
        return True

    def unregister_mod(self, mod_id: str) -> bool:
        if mod_id not in self._mods:
            logger.warning(f"Mod {mod_id} is not registered")
            return False

        del self._mods[mod_id]
        if mod_id in self._mod_instances:
            del self._mod_instances[mod_id]
        logger.info(f"Mod unregistered: {mod_id}")
        return True

    def get_mod_metadata(self, mod_id: str) -> Optional[ModMetadata]:
        return self._mods.get(mod_id)

    def list_mods(self) -> List[ModMetadata]:
        return list(self._mods.values())

    def list_mod_ids(self) -> List[str]:
        return list(self._mods.keys())

    def register_mod_instance(self, mod_id: str, instance: object):
        self._mod_instances[mod_id] = instance

    def get_mod_instance(self, mod_id: str) -> Optional[object]:
        return self._mod_instances.get(mod_id)


def get_mod_registry() -> ModRegistry:
    return ModRegistry.get_instance()