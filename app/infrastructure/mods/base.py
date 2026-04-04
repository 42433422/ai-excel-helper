"""
Mod Base Class
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


class Mod(ABC):
    metadata = None

    @abstractmethod
    def init(self) -> bool:
        """Initialize the mod. Return True if successful."""
        return True

    @abstractmethod
    def register_blueprints(self, app: "Flask"):
        """Register Flask blueprints to the app."""
        pass

    def cleanup(self):
        """Cleanup resources when mod is unloaded."""
        pass

    def get_hooks(self) -> List[str]:
        """Return list of hook names this mod subscribes to."""
        return []