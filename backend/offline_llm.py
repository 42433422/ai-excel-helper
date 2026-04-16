"""
离线 LLM 客户端适配层 — 通过 Ollama 本地模型提供 OpenAI 兼容接口。

使用方式与 openai.OpenAI 一致，使 planner / text-to-pandas / schema-service
无需修改调用代码即可切换到离线模式。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Iterator

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_BASE = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5:7b"
_REQUEST_TIMEOUT = 120.0


class _ChatCompletionMessage:
    """模拟 openai 类型消息对象。"""

    def __init__(self, content: str | None, tool_calls: list[Any] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _Choice:
    """模拟 openai choices 对象。"""

    def __init__(
        self,
        message: _ChatCompletionMessage,
        finish_reason: str = "stop",
    ):
        self.message = message
        self.finish_reason = finish_reason


class _Delta:
    """模拟流式 delta 对象。"""

    def __init__(self, content: str | None = None, tool_calls: list[Any] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _StreamChoice:
    """模拟流式 choice 对象。"""

    def __init__(self, delta: _Delta, finish_reason: str | None = None):
        self.delta = delta
        self.finish_reason = finish_reason


class _ToolCall:
    """模拟 tool_call 对象。"""

    def __init__(self, id: str, function: dict[str, str]):
        self.id = id
        self.index = 0
        self.function = _Function(function.get("name", ""), function.get("arguments", ""))


class _Function:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _Completions:
    """chat.completions 命名空间。"""

    def __init__(self, base_url: str, model: str, timeout: float):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def create(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float | None = None,
        response_format: dict[str, str] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any:
        mdl = model or self._model
        if stream:
            return self._stream_create(mdl, messages, tools, tool_choice, temperature, response_format)
        return self._nonstream_create(mdl, messages, tools, tool_choice, temperature, response_format)

    def _build_payload(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        temperature: float | None,
        response_format: dict[str, str] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = self._convert_tools(tools)
        if tool_choice:
            payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature
        if response_format and response_format.get("type") == "json_object":
            fmt_msg = (
                "IMPORTANT: You must respond with a valid JSON object only. "
                "Do NOT wrap it in markdown code fences or add any text before/after the JSON."
            )
            messages = list(messages)
            if messages and messages[0].get("role") == "system":
                messages[0] = {**messages[0], "content": messages[0]["content"] + "\n\n" + fmt_msg}
            else:
                messages.insert(0, {"role": "system", "content": fmt_msg})
            payload["messages"] = messages
        return payload

    @staticmethod
    def _convert_tools(openai_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """将 OpenAI tools 格式转换为 Ollama 格式（基本兼容）。"""
        converted = []
        for t in openai_tools:
            fn = t.get("function", {})
            converted.append({
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", {}),
                },
            })
        return converted

    def _nonstream_create(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        temperature: float | None,
        response_format: dict[str, str] | None,
    ) -> Any:
        payload = self._build_payload(model, messages, tools, tool_choice, temperature, response_format)
        url = f"{self._base_url}/v1/chat/completions"
        t0 = time.perf_counter()
        try:
            resp = httpx.post(url, json=payload, timeout=self._timeout)
            resp.raise_for_status()
        except httpx.ConnectError:
            raise RuntimeError(
                f"无法连接到 Ollama 服务 ({url})。请确认 Ollama 已启动：运行 `ollama serve`"
            ) from None
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama 请求失败 ({e.response.status_code}): {e.response.text}") from None

        data = resp.json()
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info("offline_llm non-stream model=%s duration_ms=%s", model, duration_ms)

        return self._parse_response(data)

    def _stream_create(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        temperature: float | None,
        response_format: dict[str, str] | None,
    ) -> Any:
        payload = self._build_payload(model, messages, tools, tool_choice, temperature, response_format)
        payload["stream"] = True
        url = f"{self._base_url}/v1/chat/completions"
        try:
            with httpx.stream("POST", url, json=payload, timeout=self._timeout) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        yield self._parse_stream_chunk(chunk)
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError:
            raise RuntimeError(f"无法连接到 Ollama 服务 ({url})。请确认 Ollama 已启动：运行 `ollama serve`") from None

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> Any:
        """将 Ollama 响应解析为 OpenAI SDK 兼容格式。"""
        class _Response:
            def __init__(self):
                self.choices: list[_Choice] = []

        resp = _Response()
        choices = data.get("choices", [])
        for c in choices:
            msg_data = c.get("message", {})
            content = msg_data.get("content")
            tool_calls_raw = msg_data.get("tool_calls")
            tool_calls = None
            if tool_calls_raw:
                tool_calls = [
                    _ToolCall(tc.get("id", f"call_{i}"), tc.get("function", {}))
                    for i, tc in enumerate(tool_calls_raw)
                ]
            resp.choices.append(_Choice(_ChatCompletionMessage(content, tool_calls), c.get("finish_reason", "stop")))
        return resp

    @staticmethod
    def _parse_stream_chunk(chunk: dict[str, Any]) -> Any:
        """将 SSE chunk 解析为 OpenAI SDK 兼容格式。"""
        class _ChunkResp:
            def __init__(self):
                self.choices: list[_StreamChoice] = []

        resp = _ChunkResp()
        choices = chunk.get("choices", [])
        for c in choices:
            delta_data = c.get("delta", {})
            content = delta_data.get("content")
            tc_raw = delta_data.get("tool_calls")
            tcs = None
            if tc_raw:
                tcs = [
                    _ToolCall(tc.get("id", f"call_{i}"), tc.get("function", {}))
                    for i, tc in enumerate(tc_raw)
                ]
            resp.choices.append(_StreamChoice(_Delta(content, tcs), c.get("finish_reason")))
        return resp


class OfflineClient:
    """
    模拟 openai.OpenAI 接口的离线客户端，通过 Ollama 本地模型运行。

    用法：
        cli = OfflineClient(base_url="http://localhost:11434/v1", model="qwen2.5:7b")
        resp = cli.chat.completions.create(model="qwen2.5:7b", messages=[...])
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str = "ollama",
        timeout: float | None = None,
    ):
        resolved_base = (base_url or os.environ.get("OLLAMA_BASE_URL", "")).rstrip("/")
        if not resolved_base:
            resolved_base = f"{_DEFAULT_OLLAMA_BASE}/v1"
        elif not resolved_base.endswith("/v1"):
            resolved_base = f"{resolved_base}/v1"
        self._base_url = resolved_base
        self._model = model or os.environ.get("OLLAMA_MODEL", _DEFAULT_MODEL)
        self._api_key = api_key
        self._timeout = timeout or _REQUEST_TIMEOUT
        self.chat = _Completions(resolved_base, self._model, self._timeout)


def check_ollama_available() -> tuple[bool, list[str]]:
    """
    检查 Ollama 服务是否可用。
    返回 (是否可用, 模型列表)。
    """
    base = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE).rstrip("/")
    try:
        resp = httpx.get(f"{base}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
        return False, []
    except Exception:
        return False, []


def get_offline_client(**kwargs: Any) -> OfflineClient:
    """工厂函数：根据环境变量或参数创建 OfflineClient。"""
    return OfflineClient(**kwargs)


def pull_model_stream(model_name: str):
    """
    流式下载 Ollama 模型，yield 每行进度状态。
    """
    base = os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE).rstrip("/")
    url = f"{base}/api/pull"
    try:
        with httpx.stream("POST", url, json={"name": model_name}, timeout=300.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    yield line
    except Exception as e:
        yield json.dumps({"error": str(e)})
