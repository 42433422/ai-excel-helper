"""
通过微信进程在 Windows 音频会话中的 Active 状态，判断是否在持续占用声音；
持续超过阈值后再允许上层做屏幕模板匹配（避免无来电时全屏轮询）。

依赖（可选）：pycaw、comtypes（未安装时上层应回退为「不门控」行为）。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_warned_no_pycaw = False
_warned_enum_error = False
_pycaw_ok: Optional[bool] = None

# 进程名子串（国内版常为 Weixin.exe）
_WECHAT_NAME_MARKERS = ("wechat", "weixin")


def _pycaw_available() -> bool:
    global _pycaw_ok
    if _pycaw_ok is not None:
        return _pycaw_ok
    try:
        from pycaw.pycaw import AudioUtilities  # noqa: F401
        from pycaw.constants import AudioSessionState  # noqa: F401

        _pycaw_ok = True
    except ImportError:
        _pycaw_ok = False
    return _pycaw_ok


def is_wechat_audio_session_active() -> bool:
    """
    当前是否存在「微信相关进程」且会话状态为 Active 的音频会话。
    枚举失败时返回 False。
    """
    global _warned_enum_error
    if not _pycaw_available():
        return False
    from pycaw.pycaw import AudioUtilities
    from pycaw.constants import AudioSessionState

    with _lock:
        try:
            sessions = AudioUtilities.GetAllSessions()
        except Exception as e:
            if not _warned_enum_error:
                logger.warning("WeChat audio gate: GetAllSessions failed: %s", e)
                _warned_enum_error = True
            return False

    for session in sessions:
        try:
            proc = session.Process
            if proc is None:
                continue
            name = (proc.name() or "").lower()
            if not any(m in name for m in _WECHAT_NAME_MARKERS):
                continue
            if session.State == AudioSessionState.Active:
                return True
        except Exception:
            continue
    return False


class WechatAudioGate:
    """
    跟踪微信音频会话是否已连续 Active 超过 threshold_sec。
    若未安装 pycaw，update_and_should_run_template() 恒为 True（不门控，兼容旧行为）。
    """

    def __init__(self, threshold_sec: float = 2.0) -> None:
        self._threshold = max(0.1, float(threshold_sec))
        self._active_since: Optional[float] = None

    def update_and_should_run_template(self) -> bool:
        global _warned_no_pycaw
        if not _pycaw_available():
            if not _warned_no_pycaw:
                logger.info(
                    "WeChat audio gate: pycaw 未安装，屏幕模板将不按「微信占声>%.1fs」门控；"
                    "可 pip install pycaw comtypes",
                    self._threshold,
                )
                _warned_no_pycaw = True
            return True

        now = time.time()
        if not is_wechat_audio_session_active():
            self._active_since = None
            return False
        if self._active_since is None:
            self._active_since = now
        return (now - self._active_since) >= self._threshold

    def is_audio_session_active(self) -> bool:
        if not _pycaw_available():
            return False
        return is_wechat_audio_session_active()

    def active_elapsed_sec(self) -> float:
        if self._active_since is None:
            return 0.0
        return max(0.0, time.time() - self._active_since)
