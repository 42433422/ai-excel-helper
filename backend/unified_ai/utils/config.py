"""
配置管理模块
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIConfig:
    REFLEX_TIMEOUT_MS: int = 1
    CACHE_TIMEOUT_MS: int = 10
    RULE_TIMEOUT_MS: int = 50
    LLM_TIMEOUT_MS: int = 10000

    ENABLE_REFLEX: bool = True
    ENABLE_CACHE: bool = True
    ENABLE_RULES: bool = True
    ENABLE_LLM: bool = True
    FALLBACK_ON_ERROR: bool = True

    DEFAULT_LLM: str = "deepseek-chat"
    FALLBACK_LLM: str = "offline"

    CACHE_SIZE: int = 1000
    CACHE_TTL_SECONDS: int = 300

    LOG_LEVEL: str = "INFO"
    LOG_PROCESSING_DETAILS: bool = True

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "AIConfig":
        return cls(**{k: v for k, v in config.items() if hasattr(cls, k)})


_config: AIConfig | None = None


def get_config() -> AIConfig:
    global _config
    if _config is None:
        _config = AIConfig()
    return _config
