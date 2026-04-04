from __future__ import annotations

import asyncio
import base64
import re
import threading
from dataclasses import dataclass
from collections import OrderedDict
from typing import Dict, Optional, Tuple

DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
_CACHE_MAX_SIZE = 50

_EDGE_VOICE_RE = re.compile(r"^[a-z]{2,3}-[A-Z]{2,3}-[A-Za-z]+Neural$")
_TTS_CACHE: "OrderedDict[Tuple[str, str, str, str, str], Dict[str, str]]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_WARMUP_STARTED = False
_WARMUP_LOCK = threading.Lock()

_HARDCODED_PRO_PHRASES = [
    "您好，我是修茈。我可以帮您控制整个系统：产品管理、原材料仓库、出货单、客户管理、标签打印等。请告诉我您需要做什么？",
    "您好，我是修茈，可以协助您处理产品、原材料、出货单、客户和标签打印。",
    "我可以帮您控制整个系统，请告诉我您现在要做什么。",
    "您好，我是您的 AI 助理，目前已经开始实时监控，很高兴为您处理发货单相关事宜",
    "已识别发货单，正在自动生成...",
    "已自动打印发货单。",
    "自动打印请求失败",
    "工具执行成功",
    "任务执行完成",
    "请补充必要信息后继续。",
    "已退出工作模式，球体已恢复为青色；监控列表与每 10 秒刷新已停止。",
    "您好！我是 XCAGI 智能助手，很高兴为您服务！",
    "您好！欢迎使用 XCAGI 系统！",
    "今天需要我帮您做什么？",
]

_COMMON_PHRASES = [
    "好的",
    "收到您的需求",
    "正在处理",
    "请稍等",
    "我已记录",
    "马上为您执行",
    "已开始执行",
    "执行完成",
    "任务已完成",
    "结果已更新",
    "已为您生成",
    "正在为您查询",
    "查询完成",
    "正在为您整理",
    "整理完成",
    "正在加载数据",
    "加载完成",
    "已成功保存",
    "保存完成",
    "修改已生效",
    "设置已更新",
    "已为您提交",
    "提交成功",
    "请确认以下信息",
    "请补充必要信息",
    "参数不完整",
    "输入格式有误",
    "暂未找到匹配结果",
    "已找到相关结果",
    "正在优化答案",
    "已为您切换到专业模式",
    "专业模式已开启",
    "正在调用工具",
    "工具调用成功",
    "正在重试",
    "重试成功",
    "网络稍慢，请稍后",
    "系统繁忙，请稍后再试",
    "已为您创建任务",
    "任务正在后台运行",
    "后台任务已结束",
    "正在为您生成发货单",
    "发货单生成完成",
    "正在准备打印内容",
    "打印内容已准备好",
    "已为您解析产品信息",
    "产品信息解析完成",
    "正在同步数据",
    "数据同步完成",
    "感谢您的等待",
    "请告诉我您需要做什么",
]


def _build_warmup_phrases(limit: int) -> list[str]:
    merged = [*_HARDCODED_PRO_PHRASES, *_COMMON_PHRASES]
    ordered_unique: list[str] = []
    seen: set[str] = set()
    for phrase in merged:
        text = (phrase or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered_unique.append(text)
        if len(ordered_unique) >= limit:
            break
    return ordered_unique


@dataclass(frozen=True)
class TtsRequest:
    text: str
    voice: str = DEFAULT_EDGE_VOICE
    lang: str = "zh"
    rate: Optional[str] = None
    pitch: Optional[str] = None


def _coalesce_voice(voice: Optional[str], speaker_id: Optional[str], lang: str) -> str:
    for candidate in (voice, speaker_id):
        v = (candidate or "").strip()
        if v and _EDGE_VOICE_RE.match(v):
            return v
    # 目前只实现中文默认；未来可扩展基于 lang 选默认 voice
    _ = (lang or "").strip().lower()
    return DEFAULT_EDGE_VOICE


def _normalize_cache_key(
    *, text: str, voice: str, lang: str, rate: Optional[str], pitch: Optional[str]
) -> Tuple[str, str, str, str, str]:
    return (
        text.strip(),
        voice.strip(),
        (lang or "zh").strip().lower(),
        (rate or "").strip(),
        (pitch or "").strip(),
    )


def _get_cache(key: Tuple[str, str, str, str, str]) -> Optional[Dict[str, str]]:
    with _CACHE_LOCK:
        payload = _TTS_CACHE.get(key)
        if payload is None:
            return None
        _TTS_CACHE.move_to_end(key)
        return dict(payload)


def _set_cache(key: Tuple[str, str, str, str, str], payload: Dict[str, str]) -> None:
    with _CACHE_LOCK:
        _TTS_CACHE[key] = dict(payload)
        _TTS_CACHE.move_to_end(key)
        while len(_TTS_CACHE) > _CACHE_MAX_SIZE:
            _TTS_CACHE.popitem(last=False)


def trigger_common_tts_warmup() -> None:
    """
    后台预热 50 条高频短语，减少专业模式首轮播报时延。
    只会启动一次，不阻塞请求线程。
    """

    def _warmup_worker() -> None:
        for phrase in _build_warmup_phrases(_CACHE_MAX_SIZE):
            try:
                synthesize_to_data_uri(text=phrase, lang="zh", voice=DEFAULT_EDGE_VOICE)
            except Exception:
                # 预热失败不影响主流程；首次真实请求仍可按需合成。
                continue

    global _WARMUP_STARTED
    with _WARMUP_LOCK:
        if _WARMUP_STARTED:
            return
        _WARMUP_STARTED = True

    worker = threading.Thread(target=_warmup_worker, name="tts-common-warmup", daemon=True)
    worker.start()


async def _synthesize_mp3_bytes(req: TtsRequest) -> bytes:
    import edge_tts  # type: ignore

    kwargs: dict = {"text": req.text, "voice": req.voice}
    if req.rate:
        kwargs["rate"] = req.rate
    if req.pitch:
        kwargs["pitch"] = req.pitch
    communicate = edge_tts.Communicate(**kwargs)

    chunks: list[bytes] = []
    async for item in communicate.stream():
        if item.get("type") == "audio":
            data = item.get("data")
            if isinstance(data, (bytes, bytearray)) and data:
                chunks.append(bytes(data))
    return b"".join(chunks)


def synthesize_to_data_uri(
    *,
    text: str,
    voice: Optional[str] = None,
    speaker_id: Optional[str] = None,
    lang: str = "zh",
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> dict:
    """
    Synthesize speech via Edge TTS and return a JSON-serializable payload:
    {
      "audioBase64": "data:audio/mpeg;base64,...",
      "voice": "...",
      "lang": "..."
    }
    """
    text_norm = (text or "").strip()
    if not text_norm:
        raise ValueError("text is empty")

    chosen_voice = _coalesce_voice(voice, speaker_id, lang)
    normalized_lang = (lang or "zh").strip().lower()
    key = _normalize_cache_key(text=text_norm, voice=chosen_voice, lang=normalized_lang, rate=rate, pitch=pitch)
    cache_hit = _get_cache(key)
    if cache_hit:
        return cache_hit

    req = TtsRequest(text=text_norm, voice=chosen_voice, lang=normalized_lang, rate=rate, pitch=pitch)

    try:
        mp3_bytes = asyncio.run(_synthesize_mp3_bytes(req))
    except RuntimeError as e:
        # 兼容未来环境：如果已存在事件循环（如改成 async server），用新 loop 执行
        if "asyncio.run()" not in str(e):
            raise
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            mp3_bytes = loop.run_until_complete(_synthesize_mp3_bytes(req))
        finally:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(None)

    if not mp3_bytes:
        raise RuntimeError("edge-tts returned empty audio")

    b64 = base64.b64encode(mp3_bytes).decode("ascii")
    payload = {
        "audioBase64": f"data:audio/mpeg;base64,{b64}",
        "voice": chosen_voice,
        "lang": req.lang,
    }
    _set_cache(key, payload)
    return payload

