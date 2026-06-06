"""
统一LLM适配器 - 支持OpenAI兼容协议的多供应商切换

支持厂商: DeepSeek, 小米MiMo, OpenAI, SiliconFlow, Groq, Together AI,
         OpenRouter, 阿里云百炼, 月之暗面, MiniMax, 豆包(字节), 百度文心,
         腾讯混元, 智谱GLM, 讯飞星火, 零一万物, 阶跃星辰, 百川智能, 商汤日日新
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseLLMAdapter(ABC):
    """LLM适配器基类"""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Dict[str, Any]:
        """同步聊天补全"""
        pass

    @abstractmethod
    async def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs):
        """流式聊天补全"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前模型名称"""
        pass


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """
    OpenAI兼容协议适配器

    支持20+厂商的统一调用接口，自动处理API差异
    """

    PROVIDER_DEFAULT_URLS: Dict[str, str] = {
        "deepseek": "https://api.deepseek.com",
        "xiaomi": "https://token-plan-cn.xiaomimimo.com",
        "openai": "https://api.openai.com",
        "siliconflow": "https://api.siliconflow.cn",
        "groq": "https://api.groq.com/openai",
        "together": "https://api.together.xyz",
        "openrouter": "https://openrouter.ai/api",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode",
        "moonshot": "https://api.moonshot.cn",
        "minimax": "https://api.minimaxi.com",
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",
        "wenxin": "https://qianfan.baidubce.com/v2",
        "hunyuan": "https://api.hunyuan.cloud.tencent.com/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "xunfei": "https://spark-api-open.xf-yun.com/v1",
        "yi": "https://api.lingyiwanwu.com/v1",
        "stepfun": "https://api.stepfun.com/v1",
        "baichuan": "https://api.baichuan-ai.com/v1",
        "sensetime": "https://api.sensenova.cn/compatible-mode/v1",
    }

    DEFAULT_MODELS: Dict[str, str] = {
        "xiaomi": "mimo-v2.5-pro",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "siliconflow": "Qwen/Qwen2.5-7B-Instruct",
        "groq": "llama-3.3-70b-versatile",
        "together": "meta-llama/Llama-3-70b-chat-hf",
        "openrouter": "openai/gpt-3.5-turbo",
        "dashscope": "qwen-plus",
        "moonshot": "moonshot-v1-8k",
        "minimax": "MiniMax-Text-01",
        "doubao": "ep-20250515143000-l6zqx",  # 示例endpoint
        "wenxin": "ernie-speed-128k",
        "hunyuan": "hunyuan-lite",
        "zhipu": "glm-4-flash",
        "xunfei": "spark-lite",
        "yi": "yi-lightning",
        "stepfun": "step-1-8k",
        "baichuan": "Baichuan2-Turbo",
        "sensetime": "SenseChat-5",
    }

    ENV_KEY_MAPPING: Dict[str, List[str]] = {
        "xiaomi": ["XIAOMI_API_KEY", "MIMO_API_KEY", "XIAOMI_MIMO_API_KEY"],
        "deepseek": ["DEEPSEEK_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "siliconflow": ["SILICONFLOW_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "together": ["TOGETHER_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "dashscope": ["DASHSCOPE_API_KEY"],
        "moonshot": ["MOONSHOT_API_KEY"],
        "minimax": ["MINIMAX_API_KEY"],
        "doubao": ["DOUBAO_API_KEY", "ARK_API_KEY"],
        "wenxin": ["WENXIN_API_KEY", "QIANFAN_API_KEY", "BAIDU_QIANFAN_API_KEY"],
        "hunyuan": ["HUNYUAN_API_KEY", "TENCENT_HUNYUAN_API_KEY"],
        "zhipu": ["ZHIPU_API_KEY", "BIGMODEL_API_KEY"],
        "xunfei": ["XUNFEI_API_KEY", "SPARK_API_KEY"],
        "yi": ["YI_API_KEY", "LINGYIWANWU_API_KEY"],
        "stepfun": ["STEPFUN_API_KEY"],
        "baichuan": ["BAICHUAN_API_KEY"],
        "sensetime": ["SENSETIME_API_KEY", "SENSENOVA_API_KEY"],
    }

    def __init__(
        self, provider: str = "xiaomi", model: str = None, api_key: str = None, base_url: str = None
    ):
        """
        初始化LLM适配器

        Args:
            provider: LLM提供商标识 (默认 xiaomi)
            model: 模型名称 (可选，不设则用默认值)
            api_key: API密钥 (可选，不设则从环境变量读取)
            base_url: API基础URL (可选，不设则用默认值)
        """
        self.provider = provider.lower().strip()
        self._api_key = api_key or self._resolve_api_key(self.provider)
        self._base_url = (
            base_url.rstrip("/")
            if base_url
            else self.PROVIDER_DEFAULT_URLS.get(self.provider, "https://api.openai.com")
        )
        self._model = model or self.DEFAULT_MODELS.get(self.provider, "gpt-3.5-turbo")

        self._client: Optional[httpx.AsyncClient] = None
        self._stream_client: Optional[httpx.AsyncClient] = None

        logger.info(
            f"初始化LLM适配器: {self.provider}/{self._model} "
            f"@ {self._base_url} (Key长度: {len(self._api_key or '')})"
        )

    def _resolve_api_key(self, provider: str) -> Optional[str]:
        """从环境变量解析API Key"""
        env_names = self.ENV_KEY_MAPPING.get(provider, [f"{provider.upper()}_API_KEY"])

        for env_name in env_names:
            key = os.environ.get(env_name, "").strip()
            if key:
                logger.debug(f"从环境变量 {env_name} 读取到API Key")
                return key

        logger.warning(f"未找到 {provider} 的API Key (已检查: {env_names})")
        return None

    @property
    def provider_name(self) -> str:
        return self.provider

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        """检查是否已正确配置（有API Key）"""
        return bool(self._api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取/创建异步HTTP客户端（用于同步请求）"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            )
        return self._client

    async def _get_stream_client(self) -> httpx.AsyncClient:
        """获取/创建流式HTTP客户端"""
        if self._stream_client is None or self._stream_client.is_closed:
            self._stream_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=30.0),
                limits=httpx.Limits(max_keepalive_connections=200, max_connections=1000),
            )
        return self._stream_client

    def _normalize_base_url(self) -> str:
        """标准化基础URL，确保包含正确的版本路径"""
        url = self._base_url.rstrip("/")

        if any(url.endswith(f"/v{i}") for i in range(1, 5)):
            return url

        return f"{url}/v1"

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        执行OpenAI兼容的聊天补全（同步模式）

        Args:
            messages: 对话消息列表 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成token数
            **kwargs: 其他OpenAI API参数

        Returns:
            API响应字典 (标准OpenAI格式)

        Raises:
            ValueError: API Key未配置
            httpx.HTTPStatusError: HTTP错误
        """
        if not self._api_key:
            raise ValueError(f"[{self.provider}] API Key未配置")

        base_url = self._normalize_base_url()
        url = f"{base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        logger.debug(
            f"调用 [{self.provider}/{self._model}] "
            f"messages={len(messages)}, temp={temperature}, max_tokens={max_tokens}"
        )

        client = await self._get_client()
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()

        logger.debug(
            f"[{self.provider}] 响应成功, "
            f"choices={len(result.get('choices', []))}, "
            f"usage={result.get('usage', {})}"
        )

        return result

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ):
        """
        流式聊天补全（SSE）

        Yields:
            SSE数据行 (data: {...})
        """
        if not self._api_key:
            raise ValueError(f"[{self.provider}] API Key未配置")

        base_url = self._normalize_base_url()
        url = f"{base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            **kwargs,
        }

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

        logger.info(f"启动流式请求 [{self.provider}/{self._model}]")

        client = await self._get_stream_client()
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]

    async def close(self):
        """关闭HTTP连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._stream_client and not self._stream_client.is_closed:
            await self._stream_client.aclose()

    def __repr__(self) -> str:
        configured = "✅" if self.is_configured else "❌"
        return (
            f"<OpenAICompatibleAdapter {configured} "
            f"provider={self.provider}, model={self._model}, "
            f"key={'*' * min(len(self._api_key or ''), 8)}>"
        )
