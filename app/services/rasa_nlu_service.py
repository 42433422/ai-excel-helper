# -*- coding: utf-8 -*-
"""
RASA NLU 服务包装模块

提供 RASA NLU 的调用接口，支持嵌入式和服务器模式
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RasaNLUService:
    """
    RASA NLU 服务包装类

    支持两种模式:
    - Embedded: 直接加载模型进行推理
    - Server: 通过 HTTP 调用远程 RASA 服务
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        rasa_url: str = "http://localhost:5005",
        use_server: bool = False,
        confidence_threshold: float = 0.7
    ):
        """
        初始化 RASA NLU 服务

        Args:
            model_path: RASA 模型路径（嵌入式模式使用）
            rasa_url: RASA 服务器地址（服务器模式使用）
            use_server: 是否使用服务器模式
            confidence_threshold: 置信度阈值
        """
        self.model_path = model_path
        self.rasa_url = rasa_url
        self.use_server = use_server
        self.confidence_threshold = confidence_threshold
        self._agent = None

        if not use_server and model_path:
            self._load_model()

    def _load_model(self):
        """加载 RASA 模型（嵌入式模式）"""
        try:
            from rasa.core.agent import Agent
            from rasa.model import unpack_model

            if self.model_path and os.path.exists(self.model_path):
                self._agent = Agent.load(self.model_path)
                logger.info(f"RASA 模型加载成功: {self.model_path}")
            else:
                logger.warning(f"RASA 模型文件不存在: {self.model_path}")
        except ImportError as e:
            logger.warning(f"RASA 库未安装或导入失败: {e}")
            self._agent = None
        except Exception as e:
            logger.error(f"RASA 模型加载失败: {e}")
            self._agent = None

    async def parse(self, message: str) -> Dict[str, Any]:
        """
        解析消息获取意图和实体

        Args:
            message: 用户消息

        Returns:
            RASA 解析结果，包含 intent, entities, confidence 等
        """
        if self.use_server:
            return await self._parse_via_server(message)
        else:
            return await self._parse_via_embedded(message)

    async def _parse_via_server(self, message: str) -> Dict[str, Any]:
        """通过服务器模式解析"""
        import requests

        try:
            response = requests.post(
                f"{self.rasa_url}/model/parse",
                json={"text": message},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"RASA 服务器返回错误: {response.status_code}")
                return self._empty_result()
        except requests.exceptions.ConnectionError:
            logger.warning(f"无法连接到 RASA 服务器: {self.rasa_url}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"RASA 服务器调用失败: {e}")
            return self._empty_result()

    async def _parse_via_embedded(self, message: str) -> Dict[str, Any]:
        """通过嵌入式模式解析"""
        if self._agent is None:
            logger.warning("RASA Agent 未加载")
            return self._empty_result()

        try:
            result = await self._agent.parse_message(message)
            return result
        except Exception as e:
            logger.error(f"RASA 嵌入式解析失败: {e}")
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "intent": {"name": None, "confidence": 0.0},
            "entities": [],
            "text": "",
            "error": "RASA 服务不可用"
        }

    def get_intent_with_confidence(self, message: str) -> Tuple[Optional[str], float]:
        """
        获取意图和置信度

        Args:
            message: 用户消息

        Returns:
            (意图名称, 置信度) 元组
        """
        import asyncio
        result = asyncio.run(self.parse(message))

        if result.get("intent") and result["intent"].get("name"):
            return result["intent"]["name"], result["intent"]["confidence"]
        return None, 0.0

    def is_available(self) -> bool:
        """
        检查 RASA 服务是否可用

        Returns:
            服务是否可用
        """
        if self.use_server:
            import requests
            try:
                response = requests.get(f"{self.rasa_url}/status", timeout=2)
                return response.status_code == 200
            except:
                return False
        else:
            return self._agent is not None


_rasa_service_instance: Optional[RasaNLUService] = None

def get_rasa_nlu_service(
    model_path: Optional[str] = None,
    rasa_url: str = "http://localhost:5005",
    use_server: bool = False
) -> RasaNLUService:
    """
    获取 RASA NLU 服务单例

    Args:
        model_path: RASA 模型路径
        rasa_url: RASA 服务器地址
        use_server: 是否使用服务器模式

    Returns:
        RasaNLUService 实例
    """
    global _rasa_service_instance

    if _rasa_service_instance is None:
        _rasa_service_instance = RasaNLUService(
            model_path=model_path,
            rasa_url=rasa_url,
            use_server=use_server
        )

    return _rasa_service_instance

def reset_rasa_nlu_service():
    """重置 RASA NLU 服务单例"""
    global _rasa_service_instance
    _rasa_service_instance = None
