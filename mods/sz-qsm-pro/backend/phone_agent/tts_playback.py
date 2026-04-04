"""
TTS语音合成模块
功能：调用现有TTS服务
"""

import logging
import base64
import tempfile
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TTSPlayback:
    """TTS播放器"""

    def __init__(self):
        self._tts_service = None
        self._init_tts()

    def _init_tts(self):
        """初始化TTS服务"""
        try:
            from app.services.tts_service import synthesize_to_data_uri
            self._synthesize_func = synthesize_to_data_uri
            logger.info("TTS service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize TTS service: {e}")
            self._synthesize_func = None

    def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """合成语音"""
        if not self._synthesize_func:
            logger.warning("TTS service not available")
            return None

        try:
            result = self._synthesize_func(text=text, voice=voice, lang="zh")
            audio_base64 = result.get("audioBase64", "")

            if audio_base64.startswith("data:audio"):
                audio_base64 = audio_base64.split(",")[1]

            audio_data = base64.b64decode(audio_base64)
            logger.info(f"TTS synthesized: {len(text)} chars")
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None

    def synthesize_to_file(self, text: str, output_path: str, voice: Optional[str] = None) -> bool:
        """合成到文件"""
        audio_data = self.synthesize(text, voice)
        if not audio_data:
            return False

        try:
            with open(output_path, "wb") as f:
                f.write(audio_data)
            logger.info(f"TTS saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save TTS: {e}")
            return False

    def is_available(self) -> bool:
        """检查是否可用"""
        return self._synthesize_func is not None

# 4243342
