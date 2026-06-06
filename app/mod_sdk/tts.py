"""TTS 合成（SDK re-export）。

``synthesize_to_data_uri(text, voice=...)`` 返回 ``data:audio/…;base64,…`` 形态 URI，
Mod 中的电话业务员 / 对话面板可直接塞给前端或传入 VB-Cable 播放链路。
"""

from __future__ import annotations

from app.services.tts_service import synthesize_to_data_uri  # noqa: F401

__all__ = ["synthesize_to_data_uri"]
