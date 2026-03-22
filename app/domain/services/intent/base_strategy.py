# -*- coding: utf-8 -*-
"""
意图检测策略接口

定义各种意图检测的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IntentDetectionStrategy(ABC):
    """意图检测策略基类"""

    @abstractmethod
    def detect(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        检测消息是否符合该策略

        Args:
            message: 原始消息
            context: 可选的上下文信息

        Returns:
            是否匹配
        """
        raise NotImplementedError

    @abstractmethod
    def get_confidence(self, message: str) -> float:
        """
        获取匹配置信度

        Args:
            message: 原始消息

        Returns:
            置信度 0.0 - 1.0
        """
        raise NotImplementedError
