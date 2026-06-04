"""
修茈市场(MODstore)平台代理适配器

通过修茈市场统一LLM接口调用所有模型（一个密钥/接口 → 20+厂商）

特性：
- 统一入口：POST /api/llm/chat
- 自动路由：根据provider/model自动选择厂商
- 密钥管理：平台自动解析（用户BYOK > 平台密钥）
- 计费集成：自动钱包预授权/结算
- 智能降级：超时自动切换备用模型
- ✨ 会话集成：自动从FHD登录Session获取Token（无需手动配置）

使用方式：
    # 方式1: 环境变量全局配置
    set MODSTORE_PLATFORM_URL=http://127.0.0.1:8765
    set MODSTORE_AUTH_TOKEN=your_token  (可选，不设则从session获取)

    # 方式2: 代码中创建（推荐用于请求级别）
    adapter = ModstorePlatformAdapter.from_session(
        session_id="abc123",  # 从cookie或header获取
        request=request_obj   # FastAPI Request对象（可选）
    )

    # 方式3: 从环境变量创建
    adapter = create_modstore_adapter_from_env()
"""

from collections.abc import Iterator
import json
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union
import httpx
import logging
import os
import time

logger = logging.getLogger(__name__)


def _strip_bearer_prefix(value: str) -> str:
    token = (value or "").strip()
    if token.lower().startswith("bearer "):
        return token[7:].strip()
    return token


def _to_openai_object(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_openai_object(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_openai_object(v) for v in value]
    return value


def _normalize_stream_choice(choice: Dict[str, Any]) -> Dict[str, Any]:
    if "delta" in choice:
        return choice
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    delta: Dict[str, Any] = {}
    if message.get("content"):
        delta["content"] = message.get("content")
    if message.get("tool_calls"):
        delta["tool_calls"] = message.get("tool_calls")
    return {
        "index": choice.get("index", 0),
        "delta": delta,
        "finish_reason": choice.get("finish_reason"),
    }


def _platform_stream_payload_to_openai_chunk(data: str) -> Dict[str, Any] | None:
    raw_text = (data or "").strip()
    if not raw_text or raw_text == "[DONE]":
        return None
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"choices": [{"delta": {"content": raw_text}, "finish_reason": None}]}

    if isinstance(raw, dict) and raw.get("choices"):
        choices = raw.get("choices") or []
        return {
            **raw,
            "choices": [
                _normalize_stream_choice(c if isinstance(c, dict) else {}) for c in choices
            ],
        }

    if isinstance(raw, dict) and raw.get("type") == "error":
        raise ValueError(str(raw.get("message") or raw.get("error") or "平台模型流式错误"))

    if isinstance(raw, dict):
        content = raw.get("content") or raw.get("text") or raw.get("delta") or ""
        delta: Dict[str, Any] = {}
        if content:
            delta["content"] = str(content)
        tool_calls = raw.get("tool_calls")
        if tool_calls:
            delta["tool_calls"] = tool_calls
        finish_reason = raw.get("finish_reason")
        if delta or finish_reason:
            return {"choices": [{"delta": delta, "finish_reason": finish_reason}]}

    return None


class ModstorePlatformAdapter:
    """
    修茈市场平台代理适配器

    将LLM调用请求转发给修茈市场平台，由平台统一处理：
    - 密钥解析和选择
    - 厂商路由
    - 计费结算
    - 错误处理和重试
    """

    def __init__(
        self,
        platform_url: str = None,
        auth_token: str = None,
        user_id: int = None,
        default_provider: str = "xiaomi",
        default_model: str = "mimo-v2.5-pro",
        timeout: float = 60.0,
    ):
        """
        初始化平台代理适配器

        Args:
            platform_url: 修茈市场服务URL (如 http://localhost:8000)
                         环境变量: MODSTORE_PLATFORM_URL
            auth_token: 用户认证Token (用于身份验证)
                        环境变量: MODSTORE_AUTH_TOKEN
            user_id: 用户ID (可选，用于BYOK和计费)
                     环境变量: MODSTORE_USER_ID
            default_provider: 默认供应商 (环境变量: LLM_PROVIDER)
            default_model: 默认模型 (环境变量: LLM_MODEL)
            timeout: 请求超时时间(秒)
        """
        self.platform_url = (
            platform_url or os.environ.get("MODSTORE_PLATFORM_URL", "http://localhost:8000")
        ).rstrip("/")

        self.auth_token = _strip_bearer_prefix(
            auth_token or os.environ.get("MODSTORE_AUTH_TOKEN", "")
        )

        self.user_id = user_id or self._parse_user_id(os.environ.get("MODSTORE_USER_ID", ""))

        self.default_provider = os.environ.get("LLM_PROVIDER", default_provider).lower()
        self.default_model = os.environ.get("LLM_MODEL", default_model)
        self.timeout = timeout

        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"初始化修茈市场平台代理: {self.platform_url}, "
            f"default={self.default_provider}/{self.default_model}, "
            f"user_id={self.user_id}"
        )

    @staticmethod
    def _parse_user_id(value: str) -> Optional[int]:
        """解析用户ID"""
        if not value:
            return None
        try:
            return int(value.strip())
        except (ValueError, TypeError):
            return None

    @classmethod
    def from_session(
        cls, session_id: str = None, request: Any = None, **kwargs
    ) -> "ModstorePlatformAdapter":
        """
        从FHD登录Session创建适配器（自动获取平台Token）

        这是推荐的使用方式，可以自动利用用户登录时获取的平台Token，
        无需手动配置MODSTORE_AUTH_TOKEN环境变量。

        Args:
            session_id: FHD Session ID（从cookie或X-Session-ID header获取）
            request: FastAPI Request对象（可选，可从中自动提取session_id）
            **kwargs: 其他传递给__init__的参数

        Returns:
            配置好Token的适配器实例

        使用示例：
            # 在FastAPI路由中使用
            @router.post("/api/ai/chat")
            async def chat(request: Request, ...):
                adapter = ModstorePlatformAdapter.from_session(
                    request=request  # 自动从request提取session和token
                )
                result = await adapter.chat_completion(messages)

            # 手动指定session_id
            adapter = ModstorePlatformAdapter.from_session(
                session_id="abc123"
            )
        """
        platform_url = (
            kwargs.get("platform_url")
            or os.environ.get("XCAGI_MARKET_BASE_URL")
            or os.environ.get("MODSTORE_PLATFORM_URL", "http://127.0.0.1:8765")
        ).rstrip("/")

        request_auth = ""
        if request is not None:
            try:
                request_auth = str(request.headers.get("Authorization") or "").strip()
            except Exception:
                request_auth = ""

        auth_token = (
            kwargs.get("auth_token")
            or os.environ.get("MODSTORE_AUTH_TOKEN", "").strip()
            or _strip_bearer_prefix(request_auth)
        )

        if not auth_token and (session_id or request):
            try:
                from app.fastapi_routes.market_account import (
                    latest_session_market_token,
                    session_market_token,
                    session_id_from_request,
                )

                effective_session_id = session_id or (
                    session_id_from_request(request) if request else ""
                )

                if effective_session_id:
                    token_from_session = session_market_token(effective_session_id)
                    if token_from_session:
                        auth_token = token_from_session
                        logger.debug(
                            f"从FHD Session [{effective_session_id[:8]}...] "
                            f"获取到平台Token (长度: {len(auth_token)})"
                        )
                    else:
                        logger.warning(
                            f"FHD Session [{effective_session_id[:8]}...] "
                            f"未找到平台Token（用户可能未绑定市场账号）"
                        )
                else:
                    logger.warning("无法获取有效的Session ID")
                if not auth_token:
                    latest_token = latest_session_market_token()
                    if latest_token:
                        auth_token = latest_token
                        logger.debug("使用最近一次持久化的修茈市场Token作为模型服务凭据")
            except ImportError as e:
                logger.error(f"无法导入market_account模块: {e}")
            except Exception as e:
                logger.error(f"从Session获取Token失败: {e}", exc_info=True)

        instance = cls(
            platform_url=platform_url,
            auth_token=auth_token,
            **{k: v for k, v in kwargs.items() if k not in ("platform_url", "auth_token")},
        )

        instance._source = (
            "session" if auth_token and not os.environ.get("MODSTORE_AUTH_TOKEN") else "env"
        )

        return instance

    @classmethod
    def from_request(cls, request: Any, **kwargs) -> "ModstorePlatformAdapter":
        """
        从FastAPI Request对象创建适配器（便捷方法）

        自动从Request中提取：
        - Session ID (Cookie / Header)
        - Authorization Header
        - 平台Token

        Args:
            request: FastAPI Request对象
            **kwargs: 其他参数

        Returns:
            配置好的适配器实例
        """
        return cls.from_session(request=request, **kwargs)

    def refresh_token_from_session(self, session_id: str = None, request: Any = None) -> bool:
        """
        刷新当前适配器的Token（从Session重新获取）

        用于长时间运行的会话中Token可能过期的情况。

        Args:
            session_id: FHD Session ID
            request: FastAPI Request对象

        Returns:
            是否成功刷新Token
        """
        try:
            from app.fastapi_routes.market_account import (
                session_market_token,
                session_id_from_request,
            )

            effective_session_id = session_id or (
                session_id_from_request(request) if request else ""
            )

            if not effective_session_id:
                logger.warning("refresh_token_from_session: 无有效Session ID")
                return False

            new_token = session_market_token(effective_session_id)
            if new_token:
                old_token_len = len(self.auth_token or "")
                self.auth_token = new_token
                logger.info(
                    f"Token已刷新 [{old_token_len} → {len(new_token)} chars], "
                    f"来源: session[{effective_session_id[:8]}...]"
                )
                return True
            else:
                logger.warning("Session中未找到新Token")
                return False

        except Exception as e:
            logger.error(f"刷新Token失败: {e}", exc_info=True)
            return False

    @property
    def provider_name(self) -> str:
        return f"modstore-{self.default_provider}"

    @property
    def model_name(self) -> str:
        return self.default_model

    @property
    def is_configured(self) -> bool:
        """检查是否已配置（有platform_url即可）"""
        return bool(self.platform_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
                headers=self._build_headers(),
            )
        return self._client

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers

    def _resolve_provider_model(
        self,
        provider: str = None,
        model: str = None,
    ) -> tuple[str, str]:
        effective_provider = (provider or self.default_provider).lower()
        effective_model = model or self.default_model
        if provider is None and isinstance(effective_model, str) and "/" in effective_model:
            left, right = effective_model.split("/", 1)
            if left.strip() and right.strip():
                effective_provider = left.strip().lower()
                effective_model = right.strip()
        return effective_provider, effective_model

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str = None,
        model: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        通过修茈市场平台执行聊天补全

        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            provider: 供应商 (可选，不设则用默认)
            model: 模型名称 (可选，不设则用默认)
            **kwargs: 其他参数

        Returns:
            标准OpenAI格式的响应字典

        Raises:
            ValueError: 平台未配置或返回错误
            httpx.HTTPStatusError: HTTP错误
        """
        if not self.platform_url:
            raise ValueError("修茈市场平台URL未配置 (MODSTORE_PLATFORM_URL)")

        effective_provider, effective_model = self._resolve_provider_model(provider, model)

        url = f"{self.platform_url}/api/llm/chat"

        payload: Dict[str, Any] = {
            "provider": effective_provider,
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        if self.user_id:
            payload["user_id"] = self.user_id

        logger.debug(
            f"[Modstore] 调用平台: {effective_provider}/{effective_model}, "
            f"messages={len(messages)}, user_id={self.user_id}"
        )

        t0 = time.perf_counter()

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)

            latency_ms = (time.perf_counter() - t0) * 1000.0

            if response.status_code >= 400:
                error_text = response.text[:500]
                logger.error(f"[Modstore] 平台返回错误 {response.status_code}: {error_text}")
                raise ValueError(f"平台错误({response.status_code}): {error_text}")

            result = response.json()

            # 性能监控
            try:
                from app.neuro_bus.application_neuro_bridge import (
                    neuro_notify_ai_model_roundtrip,
                )

                neuro_notify_ai_model_roundtrip(
                    model=f"modstore:{effective_provider}/{effective_model}",
                    latency_ms=latency_ms,
                    token_count=0,
                    user_id=str(self.user_id or ""),
                )
            except Exception:
                pass

            # 标准化响应格式为OpenAI兼容格式
            normalized = self._normalize_response(result, effective_provider, effective_model)

            logger.info(
                f"[Modstore] 调用成功 [{latency_ms:.0f}ms], "
                f"key_source={result.get('key_source', 'unknown')}, "
                f"billed={result.get('billed', False)}"
            )

            return normalized

        except httpx.HTTPError as e:
            logger.error(f"[Modstore] HTTP请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"[Modstore] 调用异常: {e}", exc_info=True)
            raise

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str = None,
        model: str = None,
        **kwargs,
    ):
        """
        流式聊天补全（SSE）

        Yields:
            SSE数据行
        """
        if not self.platform_url:
            raise ValueError("修茈市场平台URL未配置")

        effective_provider, effective_model = self._resolve_provider_model(provider, model)

        url = f"{self.platform_url}/api/llm/chat/stream"

        payload: Dict[str, Any] = {
            "provider": effective_provider,
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        if self.user_id:
            payload["user_id"] = self.user_id

        logger.info(f"[Modstream] 启动流式请求: {effective_provider}/{effective_model}")

        client = await self._get_client()
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]

    def chat_completion_sync(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str = None,
        model: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """同步版平台补全，用于现有 Planner 的 OpenAI SDK 兼容调用栈。"""
        if not self.platform_url:
            raise ValueError("修茈市场平台URL未配置 (MODSTORE_PLATFORM_URL)")

        effective_provider, effective_model = self._resolve_provider_model(provider, model)
        url = f"{self.platform_url}/api/llm/chat"
        payload: Dict[str, Any] = {
            "provider": effective_provider,
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if self.user_id:
            payload["user_id"] = self.user_id

        t0 = time.perf_counter()
        with httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            headers=self._build_headers(),
        ) as client:
            response = client.post(url, json=payload)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if response.status_code >= 400:
                error_text = response.text[:500]
                logger.error("[Modstore] 平台同步返回错误 %s: %s", response.status_code, error_text)
                raise ValueError(f"平台错误({response.status_code}): {error_text}")
            result = response.json()

        try:
            from app.neuro_bus.application_neuro_bridge import neuro_notify_ai_model_roundtrip

            neuro_notify_ai_model_roundtrip(
                model=f"modstore:{effective_provider}/{effective_model}",
                latency_ms=latency_ms,
                token_count=0,
                user_id=str(self.user_id or ""),
            )
        except Exception:
            pass

        return self._normalize_response(result, effective_provider, effective_model)

    def stream_chat_completion_sync(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str = None,
        model: str = None,
        **kwargs,
    ) -> Iterator[str]:
        """同步版平台流式补全，逐条产出 SSE data payload。"""
        if not self.platform_url:
            raise ValueError("修茈市场平台URL未配置")

        effective_provider, effective_model = self._resolve_provider_model(provider, model)
        url = f"{self.platform_url}/api/llm/chat/stream"
        payload: Dict[str, Any] = {
            "provider": effective_provider,
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        if self.user_id:
            payload["user_id"] = self.user_id

        logger.info("[Modstream] 启动同步流式请求: %s/%s", effective_provider, effective_model)
        with httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            headers=self._build_headers(),
        ) as client:
            with client.stream("POST", url, json=payload) as response:
                if response.status_code >= 400:
                    error_text = response.read().decode("utf-8", errors="ignore")[:500]
                    logger.error(
                        "[Modstream] 平台同步流式返回错误 %s: %s", response.status_code, error_text
                    )
                    raise ValueError(f"平台错误({response.status_code}): {error_text}")
                current_event = ""
                for line in response.iter_lines():
                    text = (line or "").strip()
                    if not text:
                        continue
                    if text.startswith("event:"):
                        current_event = text[6:].strip().lower()
                        continue
                    if text.startswith("data:"):
                        text = text[5:].strip()
                    if text == "[DONE]":
                        break
                    if current_event in {"meta", "done"}:
                        continue
                    yield text

    def _normalize_response(
        self, raw_response: Dict[str, Any], provider: str, model: str
    ) -> Dict[str, Any]:
        """
        将修茈市场响应标准化为OpenAI格式

        修茈市场返回格式:
        {
            "ok": True,
            "content": "...",
            "usage": {...},
            "charge_amount": 0.01,
            "key_source": "platform",
            "provider": "xiaomi",
            "model": "mimo-v2.5-pro",
            ...
        }

        OpenAI标准格式:
        {
            "choices": [{
                "message": {"role": "assistant", "content": "..."},
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {...},
            "model": "..."
        }
        """
        raw_choices = raw_response.get("choices")
        if isinstance(raw_choices, list) and raw_choices:
            normalized_choices: List[Dict[str, Any]] = []
            for idx, choice in enumerate(raw_choices):
                choice_dict = choice if isinstance(choice, dict) else {}
                message = (
                    choice_dict.get("message")
                    if isinstance(choice_dict.get("message"), dict)
                    else {}
                )
                normalized_message: Dict[str, Any] = {
                    "role": message.get("role") or "assistant",
                    "content": message.get("content") or "",
                }
                if message.get("tool_calls"):
                    normalized_message["tool_calls"] = message.get("tool_calls")
                normalized_choices.append(
                    {
                        "message": normalized_message,
                        "index": choice_dict.get("index", idx),
                        "finish_reason": choice_dict.get("finish_reason", "stop"),
                    }
                )
            usage = raw_response.get("usage", {})
            usage_dict = dict(usage) if isinstance(usage, dict) else {}
            return {
                "choices": normalized_choices,
                "usage": usage_dict,
                "model": raw_response.get("model") or f"{provider}/{model}",
                "_modstore_meta": {
                    "ok": raw_response.get("ok"),
                    "provider": raw_response.get("provider"),
                    "model": raw_response.get("model"),
                    "key_source": raw_response.get("key_source"),
                    "billed": raw_response.get("billed"),
                    "charge_amount": raw_response.get("charge_amount"),
                    "conversation_id": raw_response.get("conversation_id"),
                    "request_id": raw_response.get("request_id"),
                },
            }

        content = raw_response.get("content", "")
        usage = raw_response.get("usage", {})
        tool_calls = raw_response.get("tool_calls")

        # 处理usage对象（可能是dataclass或dict）
        if hasattr(usage, "__dict__"):
            usage_dict = usage.__dict__
        else:
            usage_dict = dict(usage) if isinstance(usage, dict) else {}

        normalized = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                        **({"tool_calls": tool_calls} if tool_calls else {}),
                    },
                    "index": 0,
                    "finish_reason": "stop",
                }
            ],
            "usage": usage_dict,
            "model": f"{provider}/{model}",
            "_modstore_meta": {
                "ok": raw_response.get("ok"),
                "provider": raw_response.get("provider"),
                "model": raw_response.get("model"),
                "key_source": raw_response.get("key_source"),
                "billed": raw_response.get("billed"),
                "charge_amount": raw_response.get("charge_amount"),
                "conversation_id": raw_response.get("conversation_id"),
                "request_id": raw_response.get("request_id"),
            },
        }

        return normalized

    async def get_available_providers(self) -> List[Dict[str, Any]]:
        """
        获取当前可用的供应商列表（通过平台API）

        Returns:
            供应商信息列表
        """
        url = f"{self.platform_url}/api/llm/providers"

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                return response.json().get("providers", [])
            else:
                logger.warning(f"[Modstore] 获取供应商列表失败: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"[Modstore] 查询供应商异常: {e}")
            return []

    async def get_credential_status(self, provider: str = None) -> Dict[str, Any]:
        """
        获取指定供应商的密钥状态

        Args:
            provider: 供应商名称

        Returns:
            密钥状态信息
        """
        effective_provider = provider or self.default_provider
        url = f"{self.platform_url}/api/llm/credential-status/{effective_provider}"

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def __repr__(self) -> str:
        configured = "✅" if self.is_configured else "❌"
        source = getattr(self, "_source", "unknown")
        token_len = len(self.auth_token or "")
        return (
            f"<ModstorePlatformAdapter {configured} "
            f"url={self.platform_url}, "
            f"default={self.default_provider}/{self.default_model}, "
            f"source={source}, "
            f"token={'*' * min(token_len, 8)} ({token_len} chars), "
            f"user={self.user_id}>"
        )


def create_modstore_adapter_from_env() -> Optional[ModstorePlatformAdapter]:
    """
    从环境变量创建修茈市场适配器

    环境变量：
    - MODSTORE_PLATFORM_URL: 平台服务地址 (必须)
    - MODSTORE_AUTH_TOKEN: 认证Token (推荐)
    - MODSTORE_USER_ID: 用户ID (可选)

    Returns:
        配置好的适配器实例，如果未配置则返回None
    """
    platform_url = os.environ.get("MODSTORE_PLATFORM_URL", "").strip()

    if not platform_url:
        logger.debug("未检测到 MODSTORE_PLATFORM_URL，跳过平台模式")
        return None

    return ModstorePlatformAdapter()


class _ModstoreOpenAICompletions:
    def __init__(self, adapter: ModstorePlatformAdapter):
        self._adapter = adapter

    def create(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Any:
        if stream:
            return self._stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        result = self._adapter.chat_completion_sync(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs,
        )
        return _to_openai_object(result)

    def _stream(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Iterator[Any]:
        stream_mode = os.environ.get("XCAGI_MODSTORE_USE_NATIVE_STREAM", "").strip().lower()
        use_native_stream = stream_mode not in {"0", "false", "no", "off"}
        if not use_native_stream:
            # The local ChatView still consumes SSE, but the market stream endpoint may be
            # unavailable or proxy-buffered. Use the billed platform /api/llm/chat call and
            # adapt the completed OpenAI-compatible response into one synthetic stream chunk.
            result = self._adapter.chat_completion_sync(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                **kwargs,
            )
            choice = (result.get("choices") or [{}])[0]
            message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
            delta: Dict[str, Any] = {}
            if message.get("content"):
                delta["content"] = message.get("content")
            if message.get("tool_calls"):
                delta["tool_calls"] = message.get("tool_calls")
            yield _to_openai_object(
                {
                    "choices": [
                        {
                            "index": choice.get("index", 0),
                            "delta": delta,
                            "finish_reason": choice.get("finish_reason"),
                        }
                    ],
                    "model": result.get("model"),
                }
            )
            return

        for data in self._adapter.stream_chat_completion_sync(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            **kwargs,
        ):
            chunk = _platform_stream_payload_to_openai_chunk(data)
            if chunk is not None:
                yield _to_openai_object(chunk)


class _ModstoreOpenAIChat:
    def __init__(self, adapter: ModstorePlatformAdapter):
        self.completions = _ModstoreOpenAICompletions(adapter)


class ModstoreOpenAICompatibleClient:
    """Small OpenAI SDK-compatible facade backed by the Xiuci platform LLM API."""

    is_modstore_openai_compatible = True

    def __init__(self, adapter: ModstorePlatformAdapter):
        self.adapter = adapter
        self.chat = _ModstoreOpenAIChat(adapter)

    @property
    def default_model(self) -> str:
        return self.adapter.default_model

    @property
    def default_provider(self) -> str:
        return self.adapter.default_provider


def create_modstore_openai_client_from_request(request: Any) -> ModstoreOpenAICompatibleClient:
    return ModstoreOpenAICompatibleClient(ModstorePlatformAdapter.from_request(request=request))


# 向后兼容别名
ModstoreProxyAdapter = ModstorePlatformAdapter
