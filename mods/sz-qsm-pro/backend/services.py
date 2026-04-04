"""
深圳奇士美定制 PRO Mod - 钩子处理与电话业务员
"""

import concurrent.futures
import json
import logging
import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _phone_pywin32_installed() -> bool:
    """微信通道来电窗口监控依赖 pywin32；与 TTS / VB-Cable 无关。"""
    try:
        from phone_agent.window_monitor import WIN32_AVAILABLE

        return bool(WIN32_AVAILABLE)
    except Exception:
        return False


def _json_safe_payload(d: dict) -> dict:
    """确保 status 可 JSON 序列化（避免 numpy/Inf/NaN 等导致 json.dumps 失败）。"""
    def _walk(x):
        if isinstance(x, float) and not math.isfinite(x):
            return None
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                try:
                    out[str(k)] = _walk(v)
                except Exception:
                    out[str(k)] = None
            return out
        if isinstance(x, (list, tuple)):
            return [_walk(v) for v in x]
        return x

    try:
        cleaned = _walk(d)
        return json.loads(json.dumps(cleaned, default=str, ensure_ascii=False, allow_nan=False))
    except Exception as e:
        logger.warning("[奇士美 PRO] status JSON 序列化失败，已降级: %s", e)
        return {
            "running": False,
            "status_json_error": str(e)[:500],
        }


def _ffmpeg_available_for_status() -> bool:
    """PATH 或 imageio_ffmpeg 自带的 ffmpeg，与 vb_cable_output 解码逻辑一致。"""
    try:
        from phone_agent.vb_cable_output import resolve_ffmpeg_executable

        return bool(resolve_ffmpeg_executable())
    except Exception:
        return bool(shutil.which("ffmpeg"))


def _mp3_decode_available_for_status() -> bool:
    """ffmpeg 或 miniaudio 任一可用即可解码 Edge-TTS 的 MP3。"""
    try:
        from phone_agent.vb_cable_output import mp3_decode_tooling_available

        return bool(mp3_decode_tooling_available())
    except Exception:
        return _ffmpeg_available_for_status()


# Whisper 转写常用英文标点；回复稿多为中文标点。同一段话在状态栏会看起来像「两句不一样」。
_ASR_REPLY_STRIP_PUNCT = re.compile(
    r"[\s,，.。?？!！、·…「」『』《》\"'（）()【】\[\]:：;；—\-_]+"
)


def _normalize_spoken_text_for_compare(s: str) -> str:
    """去掉空白与常见中英文标点，用于判断 ASR 与最终回复是否同义。"""
    s = (s or "").strip()
    if not s:
        return ""
    return _ASR_REPLY_STRIP_PUNCT.sub("", s)


def _asr_text_align_with_reply_if_same(asr: str, reply: str) -> str:
    """
    若 ASR 与回复去掉标点后一致，用回复稿作为展示文本（与 ⑥ 一致）。
    常见于采音拾到本机 TTS 时 Whisper 标点与合成稿不一致。
    """
    a = _normalize_spoken_text_for_compare(asr)
    b = _normalize_spoken_text_for_compare(reply)
    if not a or not b:
        return asr
    if a == b:
        return (reply or asr).strip()
    return asr


def _pcm16le_chunk_rms(chunk: bytes) -> float:
    """单声道 s16le 一块的 RMS，用于区分静音/语音。"""
    if len(chunk) < 2:
        return 0.0
    n = len(chunk) // 2
    try:
        samples = struct.unpack("<" + "h" * n, chunk[: n * 2])
    except struct.error:
        return 0.0
    if not samples:
        return 0.0
    return (sum(x * x for x in samples) / len(samples)) ** 0.5


def _phone_rms_silence_threshold() -> float:
    """兼容旧状态接口：与 _phone_rms_speech_hi() 一致。"""
    return _phone_rms_speech_hi()


def _phone_rms_speech_hi() -> float:
    """RMS ≥ 该值视为「强语音块」并写入 buffer；对端音量小可把 XCAGI_PHONE_RMS_SPEECH 降到 80–120。"""
    try:
        v = os.environ.get("XCAGI_PHONE_RMS_SPEECH")
        if v is not None and str(v).strip() != "":
            return float(v)
        return 140.0
    except ValueError:
        return 140.0


def _phone_rms_silence_lo() -> float:
    """RMS < 该值且 buffer 非空时计为「静音块」用于句末；需明显小于 speech_hi 形成滞回。"""
    try:
        return float(os.environ.get("XCAGI_PHONE_RMS_SILENCE_LO", "95"))
    except ValueError:
        return 95.0


def _phone_min_asr_seconds() -> float:
    try:
        return float(os.environ.get("XCAGI_PHONE_MIN_ASR_SEC", "0.35"))
    except ValueError:
        return 0.35


def _phone_silence_chunks_for_flush() -> int:
    try:
        return max(5, int(os.environ.get("XCAGI_PHONE_SILENCE_CHUNKS", "18")))
    except ValueError:
        return 18


def _phone_remote_silence_hangup_sec() -> float:
    """
    自接听成功起算；若期间从未识别到对方语音则以接听时刻为起点。
    超过该秒数仍无新的有效 ASR 文本则周期性尝试点击微信「挂断」。
    0 或 off/false/disable 表示关闭。
    """
    raw = os.environ.get("XCAGI_PHONE_REMOTE_SILENCE_HANGUP_SEC", "120")
    try:
        s = str(raw).strip().lower()
        if s in ("", "0", "off", "false", "no", "disable", "disabled"):
            return 0.0
        v = float(raw)
        return max(5.0, v)
    except (TypeError, ValueError):
        return 120.0


def _phone_remote_silence_hangup_retry_sec() -> float:
    """自动挂断点击失败后，再次尝试的间隔（秒）。"""
    try:
        return max(10.0, float(os.environ.get("XCAGI_PHONE_REMOTE_SILENCE_HANGUP_RETRY_SEC", "35")))
    except (TypeError, ValueError):
        return 35.0


def _phone_signal_hint_zh(chunks_since_poll: int, peak_rms: float, speech_hi: float) -> str:
    """
    区分：① 根本没采到块（设备/回环/微信未把对方播到扬声器）② 有块但 RMS 低于阈值。
    """
    if chunks_since_poll <= 0:
        return (
            "【采音】本轮状态轮询内未收到任何 PCM 块：后端等于没拿到对方声音。"
            "请查：1) pip install soundcard numpy 是否装好；2) 微信通话是否把对方语音播到本机扬声器/耳机"
            "（回环采的是「扬声器里播出来的声」，不是麦克风）；3) 蓝牙/扬声器与 XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR 是否匹配默认输出。"
        )
    if peak_rms < speech_hi:
        return (
            f"【采音】已收到 {chunks_since_poll} 个 PCM 块，但窗口内最大 RMS={peak_rms:.1f} 仍低于语音阈值 {speech_hi:.0f}，"
            f"buffer 难以累积，会像「对方说了但后端没有」。请把环境变量 XCAGI_PHONE_RMS_SPEECH 降到 80～120 后重启 run.py，或调高系统/微信通话音量。"
        )
    return (
        f"【采音】最近窗口内有 {chunks_since_poll} 块、峰值 RMS={peak_rms:.1f} 已达阈值 {speech_hi:.0f}，"
        "若仍无 ASR，请看句末静音是否够长或 ASR 日志。"
    )


def _phone_capture_problem_zh(
    running: bool,
    started_ok: bool,
    thread_alive: Optional[bool],
    backend: Optional[str],
) -> str:
    """采音线程退出或后端未就绪时给出可操作提示。"""
    if not running:
        return ""
    if started_ok and thread_alive is False:
        return (
            "【采音故障】采音线程已结束，不会再收到 PCM（RMS 会持续≈0）。"
            "常见：WASAPI 打开 recorder 全采样率失败。请重启电话业务员并看 run.py 里 Phone ASR: loopback at … failed；"
            "确认 pip install soundcard numpy pywin32，默认播放设备为听微信的扬声器（如 Realtek），勿把 VB-Cable CABLE Input 当默认扬声器。"
        )
    if started_ok and backend == "none":
        return (
            "【采音故障】capture_backend=none：采音未成功初始化。请重启电话业务员，检查 PyAudio/soundcard 与录音设备权限。"
        )
    return ""


def _phone_capture_rms_diagnosis_zh(peak_rms: float) -> str:
    """
    供 /phone-agent/status 展示：说明 RMS 峰值（轮询窗内最大块）、双阈值分段含义。
    peak_rms：自上次 get_status 轮询以来，采音链路上各 PCM 块 RMS 的最大值（轮询后会清零）。
    """
    hi = _phone_rms_speech_hi()
    lo = _phone_rms_silence_lo()
    sil_chunks = _phone_silence_chunks_for_flush()
    return (
        f"采音诊断：RMS峰值≈{peak_rms:.1f}（轮询间隔内各块 RMS 的最大值，取后清零）；"
        f"语音块阈值≥{hi:.0f}；句末静音块 RMS＜{lo:.0f}，连续 {sil_chunks} 块后送 ASR。"
        f"分段用双阈值滞回：对端小声时须多块 RMS 常≥语音阈值才会入 buffer，否则会像「没收到声音」；"
        f"可把环境变量 XCAGI_PHONE_RMS_SPEECH 降到 80–120 再试。"
    )


def _phone_capture_who_zh(ac_backend: Optional[str]) -> str:
    """
    说明「用户说话」与「采音通路」的关系，避免误以为默认回环会采到麦克风。
    """
    use_mic = (os.environ.get("XCAGI_PHONE_USE_DEFAULT_MIC") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if use_mic:
        return (
            "谁进 ASR：当前采**默认麦克风**（XCAGI_PHONE_USE_DEFAULT_MIC=1）。"
            "你说的话会进本进程；请核对 Windows/微信使用的麦克风与默认设备是否一致。"
        )
    if ac_backend == "wasapi_loopback":
        return (
            "谁进 ASR：当前为**扬声器回环**，采的是「从扬声器播放出来的声音」，用于识别**对方**在微信里说话。"
            "你对着麦克风说的话**不会**从这一路进后端（你的话走微信上行，不经本机扬声器回放）。"
            "若你要测「自己说话」是否被本进程采到，请设 XCAGI_PHONE_USE_DEFAULT_MIC=1 并重启电话业务员。"
        )
    if ac_backend == "pyaudio":
        return (
            "谁进 ASR：当前为 PyAudio **输入设备**（常为立体声混音或麦克风）。"
            "要采**微信对端**从扬声器出来的声音：优先恢复 **WASAPI 扬声器回环**（pip install soundcard numpy **与 pywin32**，"
            "重启 run.py；曾出现 0x800401f0 多为未装 pywin32）。"
            "若仍走 PyAudio：请在「声音→录制」启用**立体声混音**并让本进程选到它，或设 XCAGI_PHONE_INPUT_DEVICE_SUBSTR；"
            "仅用物理麦克风时，对端语音若不从扬声器外放，本机采不到。"
            "（勿与 VB「CABLE Input」混淆：那是 TTS **播放**端，不是本处 ASR 输入。）"
        )
    return (
        "谁进 ASR：采音未就绪或后端未知；请查看 phone_capture_backend、phone_asr_input_device_label，"
        "并确认已启动电话业务员且 soundcard/PyAudio 可用。"
    )


_phone_agent_manager = None
_phone_agent_lock = threading.Lock()


def get_phone_agent_manager():
    """获取电话业务员管理器单例"""
    global _phone_agent_manager
    with _phone_agent_lock:
        if _phone_agent_manager is None:
            _phone_agent_manager = PhoneAgentManager()
        return _phone_agent_manager


class PhoneAgentManager:
    """电话业务员管理器 - 整合所有模块"""
    OPENING_LINE = "您好，这里是奇士美业务员，请问有什么可以帮您？"
    OPENING_COOLDOWN_SEC = 12.0

    def __init__(self):
        self._phone_channel = "wechat"
        self._window_monitor = None
        self._audio_capture = None
        self._asr_processor = None
        self._intent_handler = None
        self._response_generator = None
        self._tts_playback = None
        self._vb_cable_output = None
        self._running = False
        self._process_thread = None
        self._ui_lock = threading.Lock()
        self._last_popup_detected_at_ms = None
        self._last_popup_source = None
        self._last_popup_title = None
        self._last_popup_class_name = None
        self._last_popup_hwnd = None
        self._last_popup_w = None
        self._last_popup_h = None
        self._last_click_at_ms = None
        self._last_click_ok = None
        self._last_click_method = None
        self._last_click_x = None
        self._last_click_y = None
        self._last_click_error = None
        self._last_opening_at = 0.0
        self._opening_lock = threading.Lock()
        self._last_opening_at_ms = None
        self._last_opening_ok = None
        self._last_opening_error = None
        self._last_call_ended_at_ms = None
        self._last_call_end_reason = None
        self._last_asr_text = None
        self._last_asr_at_ms = None
        self._last_reply_text = None
        self._last_reply_at_ms = None
        self._last_pipeline_error = None
        # 最近一次已成功送入 VB 的合成音（去标点），用于识别「输出被麦克风/回环采回」的回授
        self._last_played_tts_norm: Optional[str] = None
        self._capture_peak_lock = threading.Lock()
        self._capture_peak_rms = 0.0
        self._capture_chunk_count_since_poll = 0
        self._audio_capture_started_ok = False
        self._hangup_state_lock = threading.Lock()
        self._voice_call_session_active = False
        self._voice_call_answered_monotonic: Optional[float] = None
        self._last_remote_asr_monotonic: Optional[float] = None
        self._last_remote_hangup_attempt_monotonic: Optional[float] = None
        self._remote_hangup_check_at = 0.0
        self._asr_executor = None
        self._asr_backlog_sem = threading.Semaphore(8)
        self._sales_dialog = None
        self._last_start_error: Optional[str] = None
        self._adb_available = False
        self._adb_device_connected = False
        self._adb_device_serial: Optional[str] = None
        self._adb_call_state = "UNKNOWN"
        self._adb_last_poll_at_ms: Optional[int] = None
        self._adb_last_answer_at_ms: Optional[int] = None
        self._adb_last_answer_ok: Optional[bool] = None
        self._adb_last_error: Optional[str] = None
        self._adb_last_state_for_answer: Optional[str] = None
        # 管线代：来电弹窗/接听/挂断均递增，用于清空采音队列与 process_loop 内半段 buffer
        self._pipeline_generation_lock = threading.Lock()
        self._pipeline_generation = 0
        # ASR 代：仅在「接听成功」「通话结束」时递增，避免 popup+接听 双 bump 误杀响铃期间的合法分段
        self._asr_epoch_lock = threading.Lock()
        self._voice_asr_epoch = 0
        self._init_components()
        try:
            from phone_agent.sales_dialog import PhoneSalesDialog

            self._sales_dialog = PhoneSalesDialog()
        except Exception as e:
            logger.warning("[奇士美 PRO] 订购话术模块未加载: %s", e)

    def _init_components(self):
        """初始化所有组件"""
        try:
            import sys
            from pathlib import Path

            backend_dir = Path(__file__).parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))

            from phone_agent import (
                PhoneWindowMonitor,
                AudioCapture,
                ASRProcessor,
                IntentHandler,
                ResponseGenerator,
                TTSPlayback,
                VBCableOutput,
            )

            self._window_monitor = PhoneWindowMonitor()
            self._audio_capture = AudioCapture()
            self._asr_processor = ASRProcessor()
            self._intent_handler = IntentHandler()
            self._response_generator = ResponseGenerator()
            self._tts_playback = TTSPlayback()
            self._vb_cable_output = VBCableOutput()

            if self._window_monitor:
                self._window_monitor.set_event_sink(self._on_phone_ui_event)

            logger.info("[奇士美 PRO] 电话业务员组件初始化完成")
        except Exception as e:
            logger.error(f"[奇士美 PRO] 电话业务员组件初始化失败: {e}")
            import traceback
            logger.error(f"[奇士美 PRO] 堆栈跟踪: {traceback.format_exc()}")

    def _env_bool_phone(self, name: str, default: bool = False) -> bool:
        v = (os.environ.get(name) or "").strip().lower()
        if not v:
            return default
        return v in ("1", "true", "yes", "on")

    def set_phone_channel(self, channel: Optional[str]) -> None:
        c = str(channel or "").strip().lower()
        if c in ("wechat", "adb"):
            self._phone_channel = c

    def _adb_play_audio_via_phone(self, audio_data: bytes) -> bool:
        """通过 ADB 在手机上播放音频（TTS→手机扬声器）"""
        if not self._adb_device_connected or not self._adb_device_serial:
            logger.warning("[奇士美 PRO] ADB 播放：设备未连接")
            return False
        try:
            import tempfile
            import struct
            import wave

            pcm_data = self._convert_mp3_to_pcm(audio_data)
            if not pcm_data:
                logger.warning("[奇士美 PRO] ADB 播放：MP3转PCM失败")
                return False

            wav_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    wav_path = f.name
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(pcm_data)

                serial = self._adb_device_serial
                phone_path = "/data/local/tmp/xcagi_tts.wav"
                ok, out = self._run_adb_cmd(
                    ["-s", serial, "push", wav_path, phone_path],
                    timeout_sec=10.0
                )
                if not ok:
                    logger.warning("[奇士美 PRO] ADB push 失败: %s", out)
                    return False

                ok, out = self._run_adb_cmd(
                    ["-s", serial, "shell", f"chmod 644 {phone_path} && tinyplay {phone_path}"],
                    timeout_sec=10.0
                )
                if not ok:
                    logger.warning("[奇士美 PRO] tinyplay 失败: %s", out)
                    return False

                logger.info("[奇士美 PRO] ADB 音频已通过手机扬声器播放")
                return True
            finally:
                if wav_path and os.path.exists(wav_path):
                    os.unlink(wav_path)
        except Exception as e:
            logger.warning("[奇士美 PRO] ADB 播放异常: %s", e)
            return False

    def _convert_mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """将 MP3 数据转换为 PCM"""
        try:
            import io
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                return audio.raw_data
            except ImportError:
                pass

            import subprocess
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                try:
                    import imageio_ffmpeg
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                except Exception:
                    pass
            if not ffmpeg_bin:
                logger.warning("[奇士美 PRO] 无 ffmpeg，无法解码 MP3")
                return None

            proc = subprocess.Popen(
                [ffmpeg_bin, "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "pipe:1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            pcm_data, _ = proc.communicate(input=mp3_data, timeout=30)
            return pcm_data
        except Exception as e:
            logger.warning("[奇士美 PRO] MP3解码异常: %s", e)
            return None

    def _run_adb_cmd(self, args: list[str], timeout_sec: float = 3.0) -> tuple[bool, str]:
        adb_bin = shutil.which("adb")
        if not adb_bin:
            return False, "adb_not_found"
        try:
            proc = subprocess.run(
                [adb_bin, *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout_sec,
                check=False,
            )
            out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            if proc.returncode != 0:
                return False, out or f"adb_exit_{proc.returncode}"
            return True, out
        except Exception as e:
            return False, str(e)

    def _adb_refresh_device(self) -> bool:
        ok, out = self._run_adb_cmd(["devices"], timeout_sec=2.5)
        self._adb_available = ok or out != "adb_not_found"
        self._adb_device_connected = False
        self._adb_device_serial = None
        if not ok:
            self._adb_last_error = self._trunc_ui(out, 200)
            return False
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        # 首行为 "List of devices attached"
        for ln in lines[1:]:
            parts = ln.split()
            if len(parts) >= 2 and parts[1] == "device":
                self._adb_device_serial = parts[0]
                self._adb_device_connected = True
                self._adb_last_error = None
                return True
        self._adb_last_error = "no_adb_device"
        return False

    def _adb_get_call_state(self) -> str:
        if not self._adb_device_connected:
            return "UNKNOWN"
        serial = self._adb_device_serial
        prefix = ["-s", serial] if serial else []
        ok, out = self._run_adb_cmd(prefix + ["shell", "dumpsys", "telephony.registry"], timeout_sec=4.0)
        if ok:
            vals = re.findall(r"mCallState\s*=\s*(\d+)", out)
            if vals:
                # 双卡时可能有多条：只要任意一条为 1，立即判定振铃。
                ivals = []
                for s in vals:
                    try:
                        ivals.append(int(s))
                    except Exception:
                        pass
                if any(v == 1 for v in ivals):
                    return "RINGING"
                if any(v == 2 for v in ivals):
                    return "OFFHOOK"
                if any(v == 0 for v in ivals):
                    return "IDLE"
            # 部分 ROM 在振铃时 mCallState 仍为 0，但 mRingingCallState 会变为非 0（常见 1/5）。
            rvals = re.findall(r"mRingingCallState\s*=\s*(\d+)", out)
            if rvals:
                for rv in rvals:
                    try:
                        # 约定：mRingingCallState != 0 一律视作振铃，优先级高于其它态。
                        if int(rv) != 0:
                            return "RINGING"
                    except Exception:
                        pass
            # 再兜底：读取精细态文本
            if re.search(r"Ringing call state:\s*[1-9]\d*", out, flags=re.IGNORECASE):
                return "RINGING"
            m = re.search(r"\bCALL_STATE_(IDLE|RINGING|OFFHOOK)\b", out)
            if m:
                return m.group(1).upper()

        # 兜底：telecom 输出在部分机型上更稳定
        ok2, out2 = self._run_adb_cmd(prefix + ["shell", "dumpsys", "telecom"], timeout_sec=4.0)
        if ok2:
            t = (out2 or "").upper()
            # 优先振铃，避免在来电窗口阶段误判为 IDLE
            if "RINGING" in t or "SET_RINGING" in t or "ENTER RINGING" in t:
                return "RINGING"
            if "OFFHOOK" in t or "ACTIVE" in t or "INCALL" in t:
                return "OFFHOOK"
            if "IDLE" in t:
                return "IDLE"

        # 更底层兜底：部分 ROM 的 dumpsys 不稳定，但 Binder service call 仍可返回 0/1/2。
        ok3, out3 = self._run_adb_cmd(prefix + ["shell", "service", "call", "phone", "2"], timeout_sec=2.5)
        if ok3:
            m3 = re.search(r"Result:\s*Parcel\(\s*([0-9a-fA-F]{8})", out3)
            if m3:
                try:
                    v3 = int(m3.group(1), 16)
                    if v3 == 1:
                        return "RINGING"
                    if v3 == 2:
                        return "OFFHOOK"
                    if v3 == 0:
                        return "IDLE"
                except Exception:
                    pass

        if not ok and not ok2 and not ok3:
            self._adb_last_error = self._trunc_ui(f"{out} | {out2} | {out3}", 220)
            return "UNKNOWN"
        self._adb_last_error = "adb_call_state_parse_failed"
        return "UNKNOWN"

    def _adb_try_answer_call(self) -> bool:
        if not self._adb_device_connected:
            self._adb_last_answer_ok = False
            self._adb_last_error = "no_adb_device"
            return False
        serial = self._adb_device_serial
        prefix = ["-s", serial] if serial else []
        ok, out = self._run_adb_cmd(prefix + ["shell", "input", "keyevent", "KEYCODE_CALL"], timeout_sec=2.0)
        if not ok:
            # 某些机型 KEYCODE_CALL 无效，尝试耳机接听键
            ok2, out2 = self._run_adb_cmd(
                prefix + ["shell", "input", "keyevent", "KEYCODE_HEADSETHOOK"],
                timeout_sec=2.0,
            )
            if ok2:
                ok = True
                out = "fallback_headsethook"
            else:
                out = f"{out} | {out2}"
        self._adb_last_answer_at_ms = int(time.time() * 1000)
        self._adb_last_answer_ok = bool(ok)
        if not ok:
            self._adb_last_error = self._trunc_ui(out, 220)
        return bool(ok)

    def _start_audio_capture_with_fallback(self) -> bool:
        """
        首次按默认策略（WASAPI 回环等）启动采音；失败且用户未显式指定麦克风时，
        自动设 XCAGI_PHONE_USE_DEFAULT_MIC=1 再试一次，使 phone-agent 能进入 running。
        （对端经扬声器的声音可能采不到，仅便于联调/先跑通流程。）
        """
        ac = self._audio_capture
        if not ac:
            return False
        if self._env_bool_phone("XCAGI_PHONE_NO_AUTO_MIC_FALLBACK", False):
            return ac.start()
        cap_ok = ac.start()
        if cap_ok:
            return True
        if self._env_bool_phone("XCAGI_PHONE_USE_DEFAULT_MIC", False):
            return False
        logger.warning(
            "[奇士美 PRO] 音频采集首次失败，自动设置 XCAGI_PHONE_USE_DEFAULT_MIC=1 后重试一次"
        )
        try:
            ac.stop()
        except Exception:
            pass
        os.environ["XCAGI_PHONE_USE_DEFAULT_MIC"] = "1"
        return ac.start()

    def start(self) -> bool:
        """启动电话业务员"""
        # 检查前端是否启用了原版模式
        try:
            from app.routes.state import read_client_mods_off_state
            if read_client_mods_off_state():
                logger.info("[奇士美 PRO] 前端已启用原版模式，跳过电话业务员启动")
                self._last_start_error = "前端已启用原版模式"
                return False
        except Exception:
            pass

        self._last_start_error = None
        if self._running:
            logger.warning("[奇士美 PRO] 电话业务员已在运行")
            return True

        if self._phone_channel == "wechat":
            if not self._window_monitor or not self._window_monitor.is_available():
                self._last_start_error = "窗口监控不可用（非 Windows 或依赖缺失）"
                logger.error("[奇士美 PRO] 窗口监控不可用")
                return False
        else:
            if not self._adb_refresh_device():
                self._last_start_error = (
                    "ADB 设备不可用：请确认已安装 adb、USB 调试已开启，并且仅连接一台在线设备。"
                )
                return False

        try:
            if self._asr_executor is None:
                self._asr_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=1,
                    thread_name_prefix="phone_asr",
                )
            if self._phone_channel == "wechat" and self._window_monitor:
                self._window_monitor.start(callback=self._on_incoming_call)
            self._audio_capture_started_ok = False
            if self._phone_channel == "wechat":
                if not self._audio_capture:
                    self._last_start_error = "音频采集组件未初始化（见后端日志：phone_agent 组件初始化失败）"
                    logger.error("[奇士美 PRO] 音频采集组件未初始化")
                    if self._window_monitor:
                        self._window_monitor.stop()
                    return False
                cap_ok = self._start_audio_capture_with_fallback()
                if not cap_ok:
                    ac_err = getattr(self._audio_capture, "last_start_error", None)
                    ac_err = (ac_err.strip() if isinstance(ac_err, str) and ac_err.strip() else None)
                    self._last_start_error = ac_err or (
                        "音频采集未启动：请在运行后端的 Python 环境中执行 pip install soundcard PyAudio numpy，"
                        "然后重启后端（run.py）；或检查 Windows 声音设备与立体声混音。"
                    )
                    logger.error(
                        "[奇士美 PRO] 音频采集启动失败（WASAPI 回环与 PyAudio 均不可用）；"
                        "请安装 soundcard、检查立体声混音/设备，或查看上文日志"
                    )
                    if self._window_monitor:
                        self._window_monitor.stop()
                    return False
                self._audio_capture_started_ok = True
                self._vb_cable_output.start()
            else:
                self._audio_capture_started_ok = False
                self._adb_last_state_for_answer = None
                self._vb_cable_output.start()

            self._running = True
            self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._process_thread.start()

            logger.info("[奇士美 PRO] 电话业务员已启动")
            return True
        except Exception as e:
            # 避免 str(e) 为空时 _last_start_error==""，上层仅显示「启动失败」而无线索
            msg = str(e).strip() or repr(e) or e.__class__.__name__
            self._last_start_error = msg[:800]
            logger.error(f"[奇士美 PRO] 电话业务员启动失败: {e}")
            self.stop()
            return False

    def stop(self):
        """停止电话业务员"""
        self._running = False
        self._audio_capture_started_ok = False

        if self._process_thread and self._process_thread.is_alive():
            self._process_thread.join(timeout=2.0)

        if self._window_monitor:
            self._window_monitor.stop()

        if self._audio_capture:
            self._audio_capture.stop()

        if self._vb_cable_output:
            self._vb_cable_output.stop()

        if self._asr_executor is not None:
            try:
                self._asr_executor.shutdown(wait=True, cancel_futures=False)
            except TypeError:
                self._asr_executor.shutdown(wait=True)
            self._asr_executor = None

        self._last_played_tts_norm = None
        if self._sales_dialog:
            try:
                self._sales_dialog.reset()
            except Exception:
                pass
        logger.info("[奇士美 PRO] 电话业务员已停止")
        with self._hangup_state_lock:
            self._voice_call_session_active = False
            self._voice_call_answered_monotonic = None
            self._last_remote_asr_monotonic = None
            self._last_remote_hangup_attempt_monotonic = None

    def _on_incoming_call(self, window):
        """来电事件回调"""
        logger.info(f"[奇士美 PRO] 收到来电: {window.get('title', '')}")

    def _reset_phone_ui_snapshot(self) -> None:
        """挂断后清空任务面板用的 ①②③ 快照（不含 last_call_ended_*，由 call_ended 事件先写入）。"""
        if self._sales_dialog:
            try:
                self._sales_dialog.reset()
            except Exception:
                pass
        with self._ui_lock:
            self._last_popup_detected_at_ms = None
            self._last_popup_source = None
            self._last_popup_title = None
            self._last_popup_class_name = None
            self._last_popup_hwnd = None
            self._last_popup_w = None
            self._last_popup_h = None
            self._last_click_at_ms = None
            self._last_click_ok = None
            self._last_click_method = None
            self._last_click_x = None
            self._last_click_y = None
            self._last_click_error = None
            self._last_opening_at_ms = None
            self._last_opening_ok = None
            self._last_opening_error = None
            self._last_asr_text = None
            self._last_asr_at_ms = None
            self._last_reply_text = None
            self._last_reply_at_ms = None
            self._last_pipeline_error = None
            self._last_played_tts_norm = None
        with self._opening_lock:
            self._last_opening_at = 0.0
        logger.info("[奇士美 PRO] 已重置电话任务面板 UI 快照（通话结束或手动清空）")

    def _bump_pipeline_generation(self, reason: str, *, bump_asr_epoch: bool) -> None:
        """递增管线代并清空采音/VB 队列；bump_asr_epoch 时同时作废尚未执行的异步 ASR 任务。"""
        n_cap = 0
        n_vb = 0
        try:
            if self._audio_capture and hasattr(self._audio_capture, "discard_queued_chunks"):
                n_cap = int(self._audio_capture.discard_queued_chunks())
        except Exception as e:
            logger.debug("[奇士美 PRO] discard capture queue: %s", e)
        try:
            if self._vb_cable_output and hasattr(self._vb_cable_output, "discard_pending_playback"):
                n_vb = int(self._vb_cable_output.discard_pending_playback())
        except Exception as e:
            logger.debug("[奇士美 PRO] discard vb queue: %s", e)
        with self._pipeline_generation_lock:
            self._pipeline_generation += 1
            pipe_gen = self._pipeline_generation
        ae = None
        if bump_asr_epoch:
            with self._asr_epoch_lock:
                self._voice_asr_epoch += 1
                ae = self._voice_asr_epoch
        logger.info(
            "[奇士美 PRO] 语音管线已重置：%s pipeline_gen=%s%s（丢弃采音块≈%s，VB 待播块≈%s）",
            reason,
            pipe_gen,
            f" asr_epoch={ae}" if ae is not None else "",
            n_cap,
            n_vb,
        )

    def _on_phone_ui_event(self, event: dict):
        """window_monitor 上报：识别弹窗 / 点击接听 / 通话结束，供 GET /phone-agent/status 展示。"""
        if not event:
            return
        kind = event.get("kind")
        try:
            if kind == "call_ended":
                self._bump_pipeline_generation("通话结束", bump_asr_epoch=True)
                with self._hangup_state_lock:
                    self._voice_call_session_active = False
                    self._voice_call_answered_monotonic = None
                    self._last_remote_asr_monotonic = None
                    self._last_remote_hangup_attempt_monotonic = None
                with self._ui_lock:
                    self._last_call_ended_at_ms = event.get("at_ms")
                    self._last_call_end_reason = event.get("reason")
                self._reset_phone_ui_snapshot()
                return
            # 必须在释放 _ui_lock 后再触发开场白：_send_opening_line 内部会再次 acquire _ui_lock，
            # 若在此处持锁调用会导致不可重入锁死锁，last_opening_* 永远不会更新。
            popup_hwnd_for_session = None
            if kind == "popup_detected":
                with self._hangup_state_lock:
                    self._voice_call_session_active = False
                    self._voice_call_answered_monotonic = None
                    self._last_remote_asr_monotonic = None
                    self._last_remote_hangup_attempt_monotonic = None
            with self._ui_lock:
                if kind == "popup_detected":
                    self._last_popup_detected_at_ms = event.get("at_ms")
                    self._last_popup_source = event.get("source")
                    self._last_popup_title = event.get("title")
                    self._last_popup_class_name = event.get("class_name")
                    self._last_popup_hwnd = event.get("hwnd")
                    self._last_popup_w = event.get("width")
                    self._last_popup_h = event.get("height")
                    self._last_call_ended_at_ms = None
                    self._last_call_end_reason = None
                    self._last_asr_text = None
                    self._last_asr_at_ms = None
                    self._last_reply_text = None
                    self._last_reply_at_ms = None
                    self._last_pipeline_error = None
                    self._last_played_tts_norm = None
                elif kind == "click_attempt":
                    self._last_click_at_ms = event.get("at_ms")
                    self._last_click_ok = event.get("ok")
                    self._last_click_method = event.get("method")
                    self._last_click_x = event.get("x")
                    self._last_click_y = event.get("y")
                    self._last_click_error = event.get("error")
                    if event.get("ok"):
                        popup_hwnd_for_session = self._last_popup_hwnd
            if kind == "popup_detected":
                self._bump_pipeline_generation("来电弹窗", bump_asr_epoch=False)
            if kind == "click_attempt" and event.get("ok"):
                # 每通接听：清冷却与队列，再播开场白并重置订购话术状态，避免沿用上通半句/话术机状态
                with self._opening_lock:
                    self._last_opening_ok = None
                    self._last_opening_error = None
                    self._last_opening_at = 0.0
                self._bump_pipeline_generation("接听成功", bump_asr_epoch=True)
                if self._sales_dialog:
                    try:
                        self._sales_dialog.reset()
                    except Exception:
                        pass
                self._maybe_send_opening_line()
                with self._hangup_state_lock:
                    self._voice_call_session_active = True
                    self._voice_call_answered_monotonic = time.monotonic()
                    self._last_remote_asr_monotonic = None
                    self._last_remote_hangup_attempt_monotonic = None
                wm = self._window_monitor
                if wm and hasattr(wm, "mark_voice_call_answered"):
                    try:
                        wm.mark_voice_call_answered(popup_hwnd_for_session)
                    except Exception as e:
                        logger.debug("[奇士美 PRO] mark_voice_call_answered: %s", e)
        except Exception as e:
            logger.debug("[奇士美 PRO] phone ui event apply failed: %s", e)

    def _maybe_send_opening_line(self) -> None:
        now = time.time()
        with self._opening_lock:
            # 仅在上一次「已成功播到 VB」后冷却；若上次解码失败，允许下一次接听立即重试，
            # 避免出现点击时间晚于开场白时间、状态仍停在旧失败记录上。
            if (
                self._last_opening_ok is True
                and now - self._last_opening_at < self.OPENING_COOLDOWN_SEC
            ):
                logger.debug(
                    "[奇士美 PRO] 开场白冷却中，跳过（距上次成功 %.1fs）",
                    now - self._last_opening_at,
                )
                return
            self._last_opening_at = now
        self._send_opening_line()

    def _send_opening_line(self) -> None:
        at_ms = int(time.time() * 1000)
        try:
            if not self._tts_playback or not self._vb_cable_output:
                logger.warning("[奇士美 PRO] 开场白播放失败：TTS 或 VB-Cable 组件不可用")
                with self._ui_lock:
                    self._last_opening_at_ms = at_ms
                    self._last_opening_ok = False
                    self._last_opening_error = "tts_or_vb_unavailable"
                return
            audio_data = self._tts_playback.synthesize(self.OPENING_LINE)
            if not audio_data:
                logger.warning("[奇士美 PRO] 开场白 TTS 合成失败")
                with self._ui_lock:
                    self._last_opening_at_ms = at_ms
                    self._last_opening_ok = False
                    self._last_opening_error = "tts_synthesize_failed"
                return

            play_ok = False
            if self._phone_channel == "adb":
                play_ok = self._adb_play_audio_via_phone(audio_data)
                if play_ok:
                    logger.info("[奇士美 PRO] 已通过 ADB 在手机上播放开场白")
            else:
                play_ok = self._vb_cable_output.play_audio(audio_data)
                if play_ok:
                    logger.info("[奇士美 PRO] 已发送电话开场白到 VB-Cable")

            if not play_ok:
                logger.warning("[奇士美 PRO] 开场白播放失败")
                with self._ui_lock:
                    self._last_opening_at_ms = at_ms
                    self._last_opening_ok = False
                    self._last_opening_error = "play_failed"
                return
            self._record_played_tts_norm(self.OPENING_LINE)
            with self._ui_lock:
                self._last_opening_at_ms = at_ms
                self._last_opening_ok = True
                self._last_opening_error = None
        except Exception as e:
            logger.warning("[奇士美 PRO] 开场白播放异常: %s", e)
            with self._ui_lock:
                self._last_opening_at_ms = at_ms
                self._last_opening_ok = False
                self._last_opening_error = str(e)[:300]

    def _maybe_auto_hangup_remote_silence(self) -> None:
        """接听后长时间无新的有效对方 ASR 文本时，尝试点击微信挂断。"""
        hang_sec = _phone_remote_silence_hangup_sec()
        if hang_sec <= 0:
            return
        retry_sec = _phone_remote_silence_hangup_retry_sec()
        now_m = time.monotonic()
        with self._hangup_state_lock:
            if not self._voice_call_session_active:
                return
            answered = self._voice_call_answered_monotonic
            last_asr = self._last_remote_asr_monotonic
            last_attempt = self._last_remote_hangup_attempt_monotonic
        if answered is None:
            return
        idle = now_m - (last_asr if last_asr is not None else answered)
        if idle < hang_sec:
            return
        if last_attempt is not None and (now_m - last_attempt) < retry_sec:
            return
        wm = self._window_monitor
        if not wm or not hasattr(wm, "try_click_hangup_in_active_call"):
            return
        clicked = wm.try_click_hangup_in_active_call()
        with self._hangup_state_lock:
            self._last_remote_hangup_attempt_monotonic = now_m
        if clicked:
            logger.info(
                "[奇士美 PRO] 已连续 %.0fs 未识别到对方新的语音（阈值 %.0fs），已尝试自动挂断",
                idle,
                hang_sec,
            )
        else:
            logger.warning(
                "[奇士美 PRO] 已超过 %.0fs 无对方有效 ASR，自动挂断点击未成功，约 %.0fs 后重试",
                hang_sec,
                retry_sec,
            )

    def _process_loop(self):
        """处理主循环 - 音频采集 -> ASR -> 意图识别 -> 回复生成 -> TTS播放"""
        logger.info("[奇士美 PRO] 处理循环已启动")

        silence_count = 0
        audio_buffer = []
        speech_hi = _phone_rms_speech_hi()
        silence_lo = _phone_rms_silence_lo()
        if speech_hi < silence_lo + 5:
            speech_hi = silence_lo + 5.0
            logger.warning(
                "[奇士美 PRO] RMS 语音阈值已调高至 speech_hi=%.0f（须大于 silence_lo）",
                speech_hi,
            )
        sil_need = _phone_silence_chunks_for_flush()
        max_seg_chunks = 380
        proc_pipe_gen = 0

        while self._running:
            try:
                if self._phone_channel == "adb":
                    self._process_adb_loop_once()
                    time.sleep(1.2)
                    continue
                with self._pipeline_generation_lock:
                    cur_gen = self._pipeline_generation
                if cur_gen != proc_pipe_gen:
                    proc_pipe_gen = cur_gen
                    audio_buffer = []
                    silence_count = 0
                now_ck = time.monotonic()
                if now_ck - self._remote_hangup_check_at >= 1.0:
                    self._remote_hangup_check_at = now_ck
                    self._maybe_auto_hangup_remote_silence()

                if not self._audio_capture:
                    time.sleep(0.2)
                    continue
                chunks = self._audio_capture.drain_chunks(64)
                if not chunks:
                    time.sleep(0.02)
                    continue
                for chunk in chunks:
                    rms = _pcm16le_chunk_rms(chunk)
                    with self._capture_peak_lock:
                        self._capture_chunk_count_since_poll += 1
                        if rms > self._capture_peak_rms:
                            self._capture_peak_rms = rms
                    # 双阈值：单阈值 550 会把「对端较小声」整块判成静音，buffer 永远攒不起来
                    if rms >= speech_hi:
                        audio_buffer.append(chunk)
                        silence_count = 0
                    elif audio_buffer:
                        if rms < silence_lo:
                            silence_count += 1
                            if silence_count >= sil_need:
                                logger.info(
                                    "[奇士美 PRO] 句末静音（RMS<%.0f 连续 %s 块），送 ASR…",
                                    silence_lo,
                                    sil_need,
                                )
                                self._submit_asr_segment(audio_buffer)
                                audio_buffer = []
                                silence_count = 0
                        else:
                            audio_buffer.append(chunk)
                            silence_count = 0
                    if len(audio_buffer) >= max_seg_chunks:
                        logger.info("[奇士美 PRO] 语音段过长，强制分段处理")
                        self._submit_asr_segment(audio_buffer)
                        audio_buffer = []
                        silence_count = 0

            except Exception as e:
                logger.error(f"[奇士美 PRO] 处理循环错误: {e}")

    def _process_adb_loop_once(self) -> None:
        now_ms = int(time.time() * 1000)
        self._adb_last_poll_at_ms = now_ms
        if not self._adb_refresh_device():
            self._adb_call_state = "UNKNOWN"
            return
        prev = self._adb_last_state_for_answer
        st = self._adb_get_call_state()
        self._adb_call_state = st
        if st == "RINGING":
            # 振铃阶段每轮仅尝试一次接听；状态切回非振铃后允许下一通再次触发。
            if self._adb_last_state_for_answer != "RINGING":
                self._adb_try_answer_call()
            with self._hangup_state_lock:
                self._voice_call_session_active = False
        elif st == "UNKNOWN":
            # 某些机型会短暂拿不到振铃态；为降低漏接，UNKNOWN 阶段做一次低频兜底尝试。
            now_ms = int(time.time() * 1000)
            last = self._adb_last_answer_at_ms or 0
            if now_ms - last >= 2500:
                self._adb_try_answer_call()
        elif st == "OFFHOOK":
            # ADB 通道接通后触发一次开场白；靠状态跃迁避免重复播报。
            if prev != "OFFHOOK":
                self._maybe_send_opening_line()
            with self._hangup_state_lock:
                self._voice_call_session_active = True
        elif st == "IDLE":
            with self._hangup_state_lock:
                self._voice_call_session_active = False
        self._adb_last_state_for_answer = st

    @staticmethod
    def _phone_reply_mode() -> str:
        """intent=仅模板；hybrid|script=未知走固定话术；llm=未知先走专业版对话模型再兜底话术。"""
        m = (os.environ.get("PHONE_AGENT_REPLY_MODE") or "hybrid").strip().lower()
        if m == "script":
            return "hybrid"
        return m

    def _try_phone_llm_reply(self, text: str) -> Optional[str]:
        try:
            from app.application import get_ai_chat_app_service

            svc = get_ai_chat_app_service()
            wrapped = (
                "【电话业务员-用一两句口语化普通话回复，不要列菜单、不要 Markdown】\n客户说："
                + (text or "").strip()
            )
            out = svc.process_chat(
                user_id="phone_agent_voice",
                message=wrapped,
                context={"intent_channel": "phone", "ui_surface": "wechat_call"},
                source="pro",
            )
            if not isinstance(out, dict) or not out.get("success"):
                return None
            r = (out.get("response") or (out.get("data") or {}).get("text") or "").strip()
            if len(r) > 600:
                r = r[:600] + "…"
            return r or None
        except Exception as e:
            logger.warning("[奇士美 PRO] 电话 LLM 回复失败，将用固定话术: %s", e)
            return None

    def _build_voice_reply(self, text: str, intent_result: Optional[Dict[str, Any]]) -> str:
        if not self._response_generator:
            return ""
        mode = self._phone_reply_mode()
        if mode == "intent":
            return self._response_generator.generate(intent_result, text) or ""

        _sales_mod = None
        try:
            from phone_agent.sales_dialog import PhoneSalesDialog as _sales_mod
        except Exception:
            pass

        def _unknown_path() -> bool:
            if _sales_mod is None:
                return False
            return _sales_mod.should_handle_unknown(intent_result)

        if not _unknown_path():
            return self._response_generator.generate(intent_result, text) or ""

        if mode == "llm":
            llm_r = self._try_phone_llm_reply(text)
            if llm_r:
                return llm_r

        if self._sales_dialog:
            try:
                scripted = self._sales_dialog.reply(text, intent_result)
                if scripted:
                    return scripted
            except Exception as e:
                logger.warning("[奇士美 PRO] 固定话术失败: %s", e)

        return self._response_generator.generate(intent_result, text) or ""

    def _submit_asr_segment(self, audio_buffer: list) -> None:
        """Whisper 与意图/TTS 在后台线程执行，不阻塞采音分段循环。"""
        if not audio_buffer:
            return
        ex = self._asr_executor
        if ex is None:
            with self._asr_epoch_lock:
                ep = self._voice_asr_epoch
            self._process_voice_segment(audio_buffer, submit_epoch=ep)
            return
        if not self._asr_backlog_sem.acquire(blocking=False):
            logger.warning("[奇士美 PRO] ASR 待处理段过多（>8），丢弃本段")
            return
        buf = list(audio_buffer)
        with self._asr_epoch_lock:
            submit_epoch = self._voice_asr_epoch

        def _run():
            try:
                self._process_voice_segment(buf, submit_epoch=submit_epoch)
            except Exception:
                logger.exception("[奇士美 PRO] ASR 线程异常")
            finally:
                self._asr_backlog_sem.release()

        try:
            ex.submit(_run)
        except Exception:
            self._asr_backlog_sem.release()
            raise

    def _process_voice_segment(self, audio_buffer: list, submit_epoch: Optional[int] = None):
        """处理一个语音段"""
        try:
            if submit_epoch is not None:
                with self._asr_epoch_lock:
                    if submit_epoch != self._voice_asr_epoch:
                        logger.info(
                            "[奇士美 PRO] 跳过已过期语音段（已挂断或新通话已开始，ASR 代不一致）"
                        )
                        return
            audio_bytes = b''.join(audio_buffer)
            sr = 16000
            if self._audio_capture and hasattr(self._audio_capture, "get_sample_rate"):
                try:
                    sr = int(self._audio_capture.get_sample_rate())
                except Exception:
                    sr = 16000
            n_samples = len(audio_bytes) // 2
            min_sec = _phone_min_asr_seconds()
            if n_samples < int(sr * min_sec):
                logger.info(
                    "[奇士美 PRO] 语音段过短（%s 样本 < %.2fs×%s），跳过 ASR",
                    n_samples,
                    min_sec,
                    sr,
                )
                return

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
                self._write_wav_header(tmp, audio_bytes)

            try:
                text = self._asr_processor.transcribe(tmp_path)
                if not text:
                    logger.info("[奇士美 PRO] ASR未能识别出文本（段长 %s 样本 @ %s Hz）", n_samples, sr)
                    return

                logger.info(f"[奇士美 PRO] 识别文本: {text}")
                at_asr = int(time.time() * 1000)

                tn = _normalize_spoken_text_for_compare(text)
                last_norm = self._last_played_tts_norm
                if tn and last_norm and tn == last_norm:
                    logger.warning(
                        "[奇士美 PRO] ASR 与最近一次已播合成音去标点后一致，判为输出回授，跳过意图与 TTS"
                    )
                    with self._ui_lock:
                        self._last_asr_text = self._trunc_ui(
                            "（回授：采音与刚播 TTS 高度一致，已忽略。请避免麦克风吹扬声器，或改用对端线路/WASAPI）",
                            200,
                        )
                        self._last_asr_at_ms = at_asr
                    return

                intent_result = self._intent_handler.recognize(text)
                response_text = self._build_voice_reply(text, intent_result)
                response_text = response_text if response_text is not None else ""

                rn = _normalize_spoken_text_for_compare(response_text)
                if tn and rn and tn == rn:
                    logger.warning(
                        "[奇士美 PRO] ASR 与本轮生成回复去标点后一致，判为本机合成回授，跳过播报"
                    )
                    with self._ui_lock:
                        self._last_asr_text = self._trunc_ui(
                            "（回授：识别与拟播话术一致，未再送 TTS。请检查采音是否拾取 VB/扬声器）",
                            200,
                        )
                        self._last_asr_at_ms = at_asr
                    return

                with self._hangup_state_lock:
                    self._last_remote_asr_monotonic = time.monotonic()

                text_for_ui = _asr_text_align_with_reply_if_same(text, response_text)
                if text_for_ui != text:
                    logger.info("[奇士美 PRO] ASR 与回复稿同义，状态展示统一为回复标点: %s", text_for_ui[:80])

                logger.info(f"[奇士美 PRO] 生成回复: {response_text}")
                at_reply = int(time.time() * 1000)
                with self._ui_lock:
                    self._last_asr_text = self._trunc_ui(text_for_ui)
                    self._last_asr_at_ms = at_asr
                    self._last_pipeline_error = None
                    self._last_reply_text = self._trunc_ui(response_text)
                    self._last_reply_at_ms = at_reply

                audio_data = self._tts_playback.synthesize(response_text)
                if audio_data:
                    play_ok = False
                    if self._phone_channel == "adb":
                        play_ok = self._adb_play_audio_via_phone(audio_data)
                        if play_ok:
                            logger.info("[奇士美 PRO] TTS音频已通过ADB在手机播放")
                    else:
                        play_ok = self._vb_cable_output.play_audio(audio_data)
                        if play_ok:
                            logger.info("[奇士美 PRO] TTS音频已发送至VB-Cable")

                    if play_ok:
                        self._record_played_tts_norm(response_text)
                    else:
                        logger.warning("[奇士美 PRO] TTS 播放失败")
                        with self._ui_lock:
                            self._last_pipeline_error = "tts_vb_play_failed"
                else:
                    logger.warning("[奇士美 PRO] TTS合成失败")
                    with self._ui_lock:
                        self._last_pipeline_error = "tts_synthesize_failed"

            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"[奇士美 PRO] 处理语音段失败: {e}")
            try:
                with self._ui_lock:
                    self._last_pipeline_error = self._trunc_ui(str(e), 160)
            except Exception:
                pass

    @staticmethod
    def _trunc_ui(s: str, n: int = 200) -> str:
        s = (s or "").strip()
        if len(s) <= n:
            return s
        return s[: n - 1] + "…"

    def _record_played_tts_norm(self, spoken: str) -> None:
        n = _normalize_spoken_text_for_compare(spoken or "")
        self._last_played_tts_norm = n if n else None

    def _write_wav_header(self, tmp_file, audio_data: bytes):
        """写入WAV文件头"""
        import struct

        sample_rate = 16000
        if self._audio_capture and hasattr(self._audio_capture, "get_sample_rate"):
            try:
                sample_rate = int(self._audio_capture.get_sample_rate())
            except Exception:
                sample_rate = 16000
        channels = 1
        bits_per_sample = 16

        data_size = len(audio_data)
        file_size = 36 + data_size

        tmp_file.write(b'RIFF')
        tmp_file.write(struct.pack('<I', file_size))
        tmp_file.write(b'WAVE')
        tmp_file.write(b'fmt ')
        tmp_file.write(struct.pack('<I', 16))
        tmp_file.write(struct.pack('<H', 1))
        tmp_file.write(struct.pack('<H', channels))
        tmp_file.write(struct.pack('<I', sample_rate))
        tmp_file.write(struct.pack('<I', sample_rate * channels * bits_per_sample // 8))
        tmp_file.write(struct.pack('<H', channels * bits_per_sample // 8))
        tmp_file.write(struct.pack('<H', bits_per_sample))
        tmp_file.write(b'data')
        tmp_file.write(struct.pack('<I', data_size))
        tmp_file.write(audio_data)

    def is_available(self) -> bool:
        """检查当前电话通道是否具备启动条件（与 TTS/VB 自检不是同一套依赖）。"""
        if self._phone_channel == "adb":
            return bool(shutil.which("adb"))
        return self._window_monitor is not None and self._window_monitor.is_available()

    def get_status(self) -> dict:
        """获取状态"""
        with self._ui_lock:
            ui_extra = {
                "last_popup_detected_at_ms": self._last_popup_detected_at_ms,
                "last_popup_source": self._last_popup_source,
                "last_popup_title": self._last_popup_title,
                "last_popup_class_name": self._last_popup_class_name,
                "last_popup_hwnd": self._last_popup_hwnd,
                "last_popup_w": self._last_popup_w,
                "last_popup_h": self._last_popup_h,
                "last_click_at_ms": self._last_click_at_ms,
                "last_click_ok": self._last_click_ok,
                "last_click_method": self._last_click_method,
                "last_click_x": self._last_click_x,
                "last_click_y": self._last_click_y,
                "last_click_error": self._last_click_error,
                "last_opening_at_ms": self._last_opening_at_ms,
                "last_opening_ok": self._last_opening_ok,
                "last_opening_error": self._last_opening_error,
                "last_call_ended_at_ms": self._last_call_ended_at_ms,
                "last_call_end_reason": self._last_call_end_reason,
                "last_asr_text": self._last_asr_text,
                "last_asr_at_ms": self._last_asr_at_ms,
                "last_reply_text": self._last_reply_text,
                "last_reply_at_ms": self._last_reply_at_ms,
                "last_pipeline_error": self._last_pipeline_error,
            }

        # ADB 通道优先返回轻量状态，避免触发与微信语音链路相关的重型探测
        # （如 VB 设备扫描/音频细节收集）导致状态接口抖动。
        if self._phone_channel == "adb":
            base_adb = {
                "running": self._running,
                "phone_channel": self._phone_channel,
                "phone_agent_last_start_error": self._last_start_error,
                "adb_available": self._adb_available,
                "adb_device_connected": self._adb_device_connected,
                "adb_device_serial": self._adb_device_serial,
                "adb_call_state": self._adb_call_state,
                "adb_last_poll_at_ms": self._adb_last_poll_at_ms,
                "adb_last_answer_at_ms": self._adb_last_answer_at_ms,
                "adb_last_answer_ok": self._adb_last_answer_ok,
                "adb_last_error": self._adb_last_error,
                "phone_pywin32_installed": _phone_pywin32_installed(),
                "phone_window_monitor_hint_zh": None,
                "window_monitor_available": False,
                "phone_in_call_ui_visible": False,
                "phone_wechat_call_session_active": False,
                "phone_agent_voice_session_active": False,
                "audio_capture_available": False,
                "phone_audio_capture_started_ok": False,
                "asr_available": False,
                "intent_handler_available": False,
                "tts_available": False,
                "vb_cable_available": False,
            }
            base_adb.update(ui_extra)
            return _json_safe_payload(base_adb)

        monitor_extra = {}
        if self._window_monitor and hasattr(self._window_monitor, "get_debug_status"):
            try:
                monitor_extra = self._window_monitor.get_debug_status() or {}
            except Exception:
                monitor_extra = {}
        vb_name = None
        vb_hz = None
        if self._vb_cable_output and hasattr(self._vb_cable_output, "get_playback_device_name"):
            try:
                vb_name = self._vb_cable_output.get_playback_device_name()
            except Exception:
                vb_name = None
        if self._vb_cable_output and hasattr(self._vb_cable_output, "get_stream_sample_rate"):
            try:
                vb_hz = self._vb_cable_output.get_stream_sample_rate()
            except Exception:
                vb_hz = None
        ac_label = None
        ac_hz = None
        if self._audio_capture and hasattr(self._audio_capture, "get_input_device_label"):
            try:
                ac_label = self._audio_capture.get_input_device_label()
            except Exception:
                ac_label = None
        if self._audio_capture and hasattr(self._audio_capture, "get_sample_rate"):
            try:
                ac_hz = int(self._audio_capture.get_sample_rate())
            except Exception:
                ac_hz = None
        ac_backend = None
        if self._audio_capture and hasattr(self._audio_capture, "get_capture_backend"):
            try:
                ac_backend = self._audio_capture.get_capture_backend()
            except Exception:
                ac_backend = None
        cap_thread_alive: Optional[bool] = None
        if self._audio_capture and hasattr(self._audio_capture, "is_capture_thread_alive"):
            try:
                cap_thread_alive = bool(self._audio_capture.is_capture_thread_alive())
            except Exception:
                cap_thread_alive = None
        peak_rms = 0.0
        chunk_since_poll = 0
        with self._capture_peak_lock:
            peak_rms = float(self._capture_peak_rms)
            chunk_since_poll = int(self._capture_chunk_count_since_poll)
            self._capture_peak_rms = 0.0
            self._capture_chunk_count_since_poll = 0
        input_devices = []
        if self._audio_capture and hasattr(self._audio_capture, "list_input_devices"):
            try:
                input_devices = self._audio_capture.list_input_devices()
            except Exception:
                input_devices = []
        phone_in_call_ui_visible = False
        phone_wechat_call_session_active = False
        if self._window_monitor:
            if hasattr(self._window_monitor, "is_in_call_ui_visible"):
                try:
                    phone_in_call_ui_visible = bool(self._window_monitor.is_in_call_ui_visible())
                except Exception:
                    phone_in_call_ui_visible = False
            if hasattr(self._window_monitor, "is_call_session_active"):
                try:
                    phone_wechat_call_session_active = bool(
                        self._window_monitor.is_call_session_active()
                    )
                except Exception:
                    phone_wechat_call_session_active = False
        hang_sec = _phone_remote_silence_hangup_sec()
        hang_retry_sec = _phone_remote_silence_hangup_retry_sec()
        idle_remote_sec = None
        voice_sess = False
        phone_agent_voice_session_active = False
        with self._hangup_state_lock:
            voice_sess = self._voice_call_session_active
            phone_agent_voice_session_active = bool(voice_sess)
            ans_m = self._voice_call_answered_monotonic
            lasr_m = self._last_remote_asr_monotonic
        if voice_sess and ans_m is not None:
            base_m = lasr_m if lasr_m is not None else ans_m
            idle_remote_sec = round(time.monotonic() - base_m, 1)
        _py_ok = _phone_pywin32_installed()
        _wm_hint = None
        if str(self._phone_channel or "").strip().lower() == "wechat":
            if not _py_ok:
                _wm_hint = (
                    "微信电话依赖 pywin32 监控来电窗口，请在运行 XCAGI 后端的同一 Python 环境中执行 pip install pywin32 后重启。"
                    "Edge-TTS、VB-Cable 单独测试不经过窗口监控，故可能「音频链路正常」但此处仍显示窗口监控不可用。"
                )
            elif self._window_monitor is None:
                _wm_hint = (
                    "phone_agent 未完整初始化（窗口监控器未创建），请查看后端日志中的「电话业务员组件初始化」。"
                )
        base = {
            "running": self._running,
            "phone_channel": self._phone_channel,
            "phone_agent_last_start_error": self._last_start_error,
            "adb_available": self._adb_available,
            "adb_device_connected": self._adb_device_connected,
            "adb_device_serial": self._adb_device_serial,
            "adb_call_state": self._adb_call_state,
            "adb_last_poll_at_ms": self._adb_last_poll_at_ms,
            "adb_last_answer_at_ms": self._adb_last_answer_at_ms,
            "adb_last_answer_ok": self._adb_last_answer_ok,
            "adb_last_error": self._adb_last_error,
            "phone_pywin32_installed": _py_ok,
            "phone_window_monitor_hint_zh": _wm_hint,
            "window_monitor_available": self._window_monitor.is_available() if self._window_monitor else False,
            "phone_in_call_ui_visible": phone_in_call_ui_visible,
            "phone_wechat_call_session_active": phone_wechat_call_session_active,
            "phone_agent_voice_session_active": phone_agent_voice_session_active,
            "audio_capture_available": self._audio_capture.is_available() if self._audio_capture else False,
            "phone_audio_capture_started_ok": bool(self._audio_capture_started_ok),
            "asr_available": self._asr_processor.is_available() if self._asr_processor else False,
            "intent_handler_available": self._intent_handler.is_available() if self._intent_handler else False,
            "tts_available": self._tts_playback.is_available() if self._tts_playback else False,
            "vb_cable_available": self._vb_cable_output.is_available() if self._vb_cable_output else False,
            "vb_cable_playback_device_name": vb_name,
            "vb_cable_stream_sample_hz": vb_hz,
            "ffmpeg_on_path": _ffmpeg_available_for_status(),
            "mp3_decode_available": _mp3_decode_available_for_status(),
            "phone_asr_input_device_label": ac_label,
            "phone_asr_input_sample_hz": ac_hz,
            "phone_capture_backend": ac_backend,
            "phone_capture_thread_alive": cap_thread_alive,
            "phone_capture_problem_zh": _phone_capture_problem_zh(
                bool(self._running),
                bool(self._audio_capture_started_ok),
                cap_thread_alive,
                ac_backend,
            ),
            "phone_capture_who_zh": _phone_capture_who_zh(ac_backend),
            "phone_whisper_model": (
                getattr(self._asr_processor, "model_size", None)
                if self._asr_processor
                else None
            ),
            "phone_whisper_backend": (
                getattr(self._asr_processor, "backend_kind", None)
                if self._asr_processor
                else None
            ),
            "phone_whisper_device": (
                getattr(self._asr_processor, "device_label", None)
                if self._asr_processor
                else None
            ),
            "phone_whisper_compute_type": (
                getattr(self._asr_processor, "compute_type_label", None)
                if self._asr_processor
                else None
            ),
            "phone_asr_rms_silence_threshold": _phone_rms_speech_hi(),
            "phone_asr_rms_speech_hi": _phone_rms_speech_hi(),
            "phone_asr_rms_silence_lo": _phone_rms_silence_lo(),
            "phone_capture_peak_rms_since_last_poll": peak_rms,
            "phone_capture_audio_chunks_since_last_poll": chunk_since_poll,
            "phone_capture_signal_hint_zh": _phone_signal_hint_zh(
                chunk_since_poll, peak_rms, _phone_rms_speech_hi()
            ),
            "phone_capture_rms_diagnosis_zh": _phone_capture_rms_diagnosis_zh(peak_rms),
            "phone_remote_silence_hangup_sec": hang_sec,
            "phone_remote_silence_hangup_retry_sec": hang_retry_sec,
            "phone_remote_silence_idle_sec": idle_remote_sec,
            "phone_remote_silence_past_hangup_threshold": (
                bool(
                    hang_sec > 0
                    and idle_remote_sec is not None
                    and idle_remote_sec >= hang_sec
                )
            ),
            "phone_input_devices": input_devices[:32],
            "phone_asr_hint": (
                "对方语音→ASR（Windows）：默认优先「WASAPI 扬声器回环」直接采正在播放到默认扬声器的声音（pip install soundcard），"
                "一般不必再开立体声混音。若微信走另一路输出，可设 XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR=扬声器名子串。"
                "禁用回环：XCAGI_PHONE_LOOPBACK=0 则仍用 PyAudio+立体声混音/指定设备。"
                "分段：XCAGI_PHONE_RMS_SPEECH（默认 140）为「语音块」下限，XCAGI_PHONE_RMS_SILENCE_LO（默认 95）以下为句末静音；"
                "仅测麦克风：XCAGI_PHONE_USE_DEFAULT_MIC=1。最短送 ASR 时长：XCAGI_PHONE_MIN_ASR_SEC（默认 0.35）。"
                "Whisper：默认 pip install faster-whisper + 模型 small（CPU int8，快且较准）；引擎 faster 优先，否则 openai。"
                "XCAGI_PHONE_WHISPER_BACKEND=openai 可强制原版；XCAGI_PHONE_WHISPER_BEAM=1 最快、=5 更准；ASR 在后台线程。"
                "长时间无新的有效对方 ASR：XCAGI_PHONE_REMOTE_SILENCE_HANGUP_SEC（默认 120，0/off 关闭）超时后尝试自动点挂断；"
                "失败后 XCAGI_PHONE_REMOTE_SILENCE_HANGUP_RETRY_SEC（默认 35）秒重试。"
            ),
            "remote_hear_tts_hint": (
                "VB-Audio（以 Windows 声音设置为准，勿按字面猜）：**CABLE Input 在「播放」列表**=往虚拟线里送声，本程序 TTS 写这里；"
                "**CABLE Output 在「录制」列表**=从虚拟线取声，微信麦克风应选它对方才能听到合成音。"
                "易混：不是「Input=录制、Output=播放」——官方命名里 Input 指线缆的注入端（系统归类为播放设备）。"
            ),
            "vb_cable_roles_zh": (
                "VB-Audio Virtual Cable：以设备在声音设置中的位置为准——**CABLE Input 仅出现在播放设备**（TTS 写入）；"
                "**CABLE Output 仅出现在录制设备**（微信麦克风）。"
                "勿记成 Input=录制、Output=播放；名称表示虚拟线方向，与「麦克风输入」口语不同。"
                "ASR 采对方语音须扬声器回环或立体声混音，勿把 CABLE Output 当对端人声来源（该路多为本机注入线缆的回送）。"
            ),
        }
        base.update(ui_extra)
        base.update(monitor_extra)
        return _json_safe_payload(base)


def on_shipment_created(shipment):
    """发货单创建后的钩子处理"""
    try:
        logger.info(f"[奇士美 PRO] 检测到新发货单：{shipment.unit_name if hasattr(shipment, 'unit_name') else '未知'}")
        
    except Exception as e:
        logger.error(f"[奇士美 PRO] 发货单钩子处理失败：{e}")


def on_product_imported(count, products):
    """产品导入后的钩子处理"""
    try:
        logger.info(f"[奇士美 PRO] 产品导入完成：{count} 个产品")
        
    except Exception as e:
        logger.error(f"[奇士美 PRO] 产品导入钩子处理失败：{e}")


def mod_init():
    """Mod初始化函数（若与包内 __init__.py 均注册，日志可能打印两次）"""
    logger.info("[奇士美 PRO] Mod初始化")
    try:
        # 延迟初始化 PhoneAgentManager，避免在 mod 加载时立即创建
        # 实际创建推迟到第一次调用 get_phone_agent_manager()
        logger.info("[奇士美 PRO] 电话业务员管理器将延迟初始化")
    except Exception as e:
        logger.error(f"[奇士美 PRO] Mod初始化失败: {e}")

# 4243342
