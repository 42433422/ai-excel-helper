"""RASA NLU 意图识别服务（深度落地版）。

此模块是 RASA 能力在 FHD 里的 **真实落地点**，提供：

1. **嵌入式** 加载 `rasa/models/*.tar.gz`（通过 ``rasa.core.agent.Agent``）。
2. **服务器** 模式通过 HTTP 调用远端 ``rasa run --enable-api``。
3. **健康探针** ``is_available()``：不仅检查变量是否设置，还会做一次
   握手（加载结果或 ``/status`` 请求）。
4. **诊断快照** ``get_status()``：供 ``/health/details``、
   ``/api/diagnostics/capabilities`` 等端点直接消费。

环境变量：

- ``RASA_MODEL_PATH``  本地模型 tar.gz 路径；为空时优先扫描 ``<repo>/rasa/models/*``。
- ``RASA_SERVER_URL``  远端服务地址，例如 ``http://localhost:5005``。
- ``RASA_USE_SERVER``  ``1`` 时强制走服务器模式。
- ``RASA_CONFIDENCE_THRESHOLD``  阈值，默认 ``0.7``。
- ``ENABLE_RASA``  ``0`` 时总开关关闭（降级为 rule-only，不再尝试加载 RASA）。

对外契约与历史 ``app/services/rasa_nlu_service.py`` 保持一致：

- ``parse(text) -> dict``（含 ``intent.name/confidence``、``entities``）
- ``get_intent_with_confidence(text) -> (intent, confidence)``
- ``is_available() -> bool``

相较于旧的 stub（固定返回 ``unk``、``load_model`` 永远 True），这里
会诚实地返回可用状态，避免「配置齐全、运行时不工作」的假阳性。
"""

from __future__ import annotations

import asyncio
import glob
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


_DEFAULT_CONFIDENCE = 0.7


def _find_latest_local_model() -> str | None:
    """在仓库内查找最新的 RASA 模型文件。

    查找顺序（取首个存在的目录）：
    - ``<repo>/rasa/models``
    - ``<repo>/XCAGI/rasa/models``

    返回按修改时间最新的 ``*.tar.gz``；找不到返回 None。
    """

    # app/ai_engines/rasa/nlu_service.py -> repo root = four levels up
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    candidates: list[str] = [
        os.path.join(repo_root, "rasa", "models"),
        os.path.join(repo_root, "XCAGI", "rasa", "models"),
    ]
    for folder in candidates:
        if not os.path.isdir(folder):
            continue
        tar_files = sorted(
            glob.glob(os.path.join(folder, "*.tar.gz")),
            key=lambda p: os.path.getmtime(p),
            reverse=True,
        )
        if tar_files:
            return tar_files[0]
    return None


class RasaNLUService:
    """RASA NLU 真实客户端（兼容旧 stub 契约）。"""

    def __init__(
        self,
        model_path: str | None = None,
        rasa_url: str | None = None,
        use_server: bool | None = None,
        confidence_threshold: float | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        enable_flag = (os.environ.get("ENABLE_RASA", "1") or "1").strip().lower()
        self._enabled = enabled if enabled is not None else enable_flag not in {"0", "false", "no"}

        self.model_path = model_path or os.environ.get("RASA_MODEL_PATH") or None
        self.rasa_url = (
            rasa_url or os.environ.get("RASA_SERVER_URL") or "http://localhost:5005"
        ).rstrip("/")

        if use_server is None:
            env_flag = (os.environ.get("RASA_USE_SERVER", "") or "").strip().lower()
            self.use_server = env_flag in {"1", "true", "yes"}
        else:
            self.use_server = bool(use_server)

        if confidence_threshold is None:
            try:
                confidence_threshold = float(
                    os.environ.get("RASA_CONFIDENCE_THRESHOLD", _DEFAULT_CONFIDENCE)
                )
            except (TypeError, ValueError):
                confidence_threshold = _DEFAULT_CONFIDENCE
        self.confidence_threshold = float(confidence_threshold)

        self._agent: Any = None
        self._load_error: str | None = None
        self._last_status: dict[str, Any] = {
            "mode": "server" if self.use_server else "embedded",
            "model_path": None,
            "agent_loaded": False,
            "server_reachable": None,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_model(self) -> bool:
        """加载模型（兼容旧接口）。

        - 嵌入式：尝试 ``Agent.load(model_path)``
        - 服务器：仅记录目标 URL，实际连通性见 ``is_available()``。
        """

        if not self._enabled:
            self._load_error = "disabled"
            return False

        if self.use_server:
            self._last_status.update({"mode": "server", "target_url": self.rasa_url})
            return True

        if not self.model_path:
            self.model_path = _find_latest_local_model()
        self._last_status["model_path"] = self.model_path

        if not self.model_path or not os.path.exists(self.model_path):
            self._load_error = f"model_not_found: {self.model_path!r}"
            return False

        try:
            from rasa.core.agent import Agent  # type: ignore
        except Exception as e:  # ImportError or its downstream side effects
            self._load_error = f"rasa_import_failed: {e}"
            return False

        try:
            self._agent = Agent.load(self.model_path)
            self._last_status["agent_loaded"] = True
            return True
        except Exception as e:
            self._load_error = f"agent_load_failed: {e}"
            self._agent = None
            return False

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def parse(self, text: str) -> dict[str, Any]:
        """同步解析（阻塞式，供规则层 / UnifiedIntentRecognizer 使用）。"""

        if not text or not str(text).strip():
            return self._empty_result("empty_text")

        if not self._enabled:
            return self._empty_result("disabled")

        if self.use_server:
            return self._parse_via_server(text)

        if self._agent is None:
            if not self.load_model():
                return self._empty_result(self._load_error or "not_loaded")
        return self._parse_via_embedded(text)

    async def parse_async(self, text: str) -> dict[str, Any]:
        """Async 包装，便于复用历史 ``async def parse`` 调用点。"""

        return await asyncio.to_thread(self.parse, text)

    def _parse_via_server(self, text: str) -> dict[str, Any]:
        try:
            import requests  # type: ignore
        except Exception as e:
            return self._empty_result(f"requests_unavailable: {e}")

        try:
            resp = requests.post(
                f"{self.rasa_url}/model/parse",
                json={"text": text},
                timeout=5,
            )
        except Exception as e:
            self._last_status["server_reachable"] = False
            return self._empty_result(f"server_unreachable: {e}")

        self._last_status["server_reachable"] = resp.status_code == 200
        if resp.status_code != 200:
            return self._empty_result(f"server_status_{resp.status_code}")

        try:
            return resp.json()
        except Exception as e:
            return self._empty_result(f"server_bad_json: {e}")

    def _parse_via_embedded(self, text: str) -> dict[str, Any]:
        try:
            # rasa 的 parse_message 是 async；这里同步等待。
            result = asyncio.run(self._agent.parse_message(text))
            return result
        except RuntimeError:
            # 已经在事件循环里 —— 用新循环兜底，避免 "asyncio.run cannot be called from a running loop"。
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._agent.parse_message(text))
            finally:
                loop.close()
        except Exception as e:
            return self._empty_result(f"parse_failed: {e}")

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def _empty_result(self, reason: str) -> dict[str, Any]:
        return {
            "intent": {"name": None, "confidence": 0.0},
            "entities": [],
            "text": "",
            "message": reason,
        }

    def is_available(self) -> bool:
        """判断 RASA 是否真正可用（不仅看配置）。"""

        if not self._enabled:
            return False
        if self.use_server:
            try:
                import requests  # type: ignore

                resp = requests.get(f"{self.rasa_url}/status", timeout=2)
                self._last_status["server_reachable"] = resp.status_code == 200
                return resp.status_code == 200
            except Exception:
                self._last_status["server_reachable"] = False
                return False
        if self._agent is None:
            self.load_model()
        return self._agent is not None

    def get_intent_with_confidence(self, text: str) -> tuple[str | None, float]:
        """取意图名 + 置信度（阈值不在此过滤，留给调用方）。"""

        result = self.parse(text)
        intent = (result.get("intent") or {}) if isinstance(result, dict) else {}
        return intent.get("name"), float(intent.get("confidence") or 0.0)

    def get_status(self) -> dict[str, Any]:
        """返回结构化状态，供健康检查/诊断端点消费。

        该方法不触发模型加载，以便健康探针廉价可用。
        """

        status = {
            "enabled": self._enabled,
            "mode": "server" if self.use_server else "embedded",
            "confidence_threshold": self.confidence_threshold,
            "model_path": self.model_path,
            "agent_loaded": self._agent is not None,
            "last_error": self._load_error,
        }
        if self.use_server:
            status["target_url"] = self.rasa_url
            status["server_reachable"] = self._last_status.get("server_reachable")
        return status


_rasa_nlu_service: RasaNLUService | None = None


def get_rasa_nlu_service() -> RasaNLUService:
    global _rasa_nlu_service
    if _rasa_nlu_service is None:
        _rasa_nlu_service = RasaNLUService()
    return _rasa_nlu_service


def reset_rasa_nlu_service() -> None:
    global _rasa_nlu_service
    _rasa_nlu_service = None


__all__ = ["RasaNLUService", "get_rasa_nlu_service", "reset_rasa_nlu_service"]
