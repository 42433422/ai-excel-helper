"""
Mod Base Class
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


class Mod(ABC):
    metadata = None

    @abstractmethod
    def init(self) -> bool:
        """Initialize the mod. Return True if successful."""
        return True

    @abstractmethod
    def register_routes(self, app: "FastAPI"):
        """Register FastAPI routes to the app."""
        pass

    def cleanup(self):
        """Cleanup resources when mod is unloaded."""
        pass

    def get_hooks(self) -> list[str]:
        """Return list of hook names this mod subscribes to."""
        return []
