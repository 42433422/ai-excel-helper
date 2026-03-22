from __future__ import annotations

import asyncio
import base64
import re
from dataclasses import dataclass
from typing import Optional

DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"

_EDGE_VOICE_RE = re.compile(r"^[a-z]{2,3}-[A-Z]{2,3}-[A-Za-z]+Neural$")


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
    req = TtsRequest(text=text_norm, voice=chosen_voice, lang=(lang or "zh").strip().lower(), rate=rate, pitch=pitch)

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
    return {
        "audioBase64": f"data:audio/mpeg;base64,{b64}",
        "voice": chosen_voice,
        "lang": req.lang,
    }

