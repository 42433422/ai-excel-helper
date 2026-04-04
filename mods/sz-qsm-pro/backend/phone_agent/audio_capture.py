"""
音频捕获模块
功能：从系统声卡捕获音频（用于电话 ASR）。

对方语音进入本机的路径（优先）：
  - Windows：WASAPI 扬声器「回环」采集（SoundCard / loopback），直接录「正在播放到该扬声器」的声音，
    不依赖「立体声混音」是否启用。需 pip install soundcard numpy。
  - 回退：PyAudio 录「录音设备」（立体声混音 / 用户指定子串 / 默认麦克风）。

勿将 VB-Cable 误作「对方」线路：
  - 播放端「CABLE Input」用于把本机 TTS 送进微信麦克风；若系统默认扬声器是它，WASAPI 回环只会采到合成音。
  - 录音端「CABLE Output」只含注入线缆的内容，同样不是扬声器里的对端声音。自动选设备时会跳过上述 VB 线路；
    显式 XCAGI_PHONE_INPUT_DEVICE_SUBSTR / XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR 仍优先尊重用户指定。

环境变量：
  XCAGI_PHONE_LOOPBACK=0        禁用回环，仅用 PyAudio
  XCAGI_PHONE_USE_DEFAULT_MIC=1 使用默认麦克风（不走回环）
  XCAGI_PHONE_INPUT_DEVICE_SUBSTR  非空时强制 PyAudio 输入设备名子串（不走回环）
  XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR  回环时匹配扬声器名称子串（如 耳机、Realtek）

Windows：若日志出现 pick loopback microphone failed: 0x800401f0（CO_E_NOTINITIALIZED），
  请 pip install pywin32；采音线程内使用 STA（CoInitializeEx）并在释放 WASAPI Recorder 之后再 CoUninitialize，
  避免 COM 与音频对象生命周期交叉导致堆损坏。
"""

import logging
import os
import sys
import threading
import queue
import time
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

from .win32_com_thread import (
    com_init_apartment_thread,
    com_uninit_apartment_thread,
    is_pythoncom_available,
)

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available, PyAudio capture disabled")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import soundcard as sc  # type: ignore
    SOUNDCARD_AVAILABLE = True
except ImportError:
    SOUNDCARD_AVAILABLE = False
    sc = None  # type: ignore
    logger.debug("SoundCard not installed: WASAPI loopback capture unavailable (pip install soundcard)")


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _norm_audio_device_name(name: str) -> str:
    return (name or "").lower().replace("vb audio", "vb-audio")


def _is_vb_cable_tts_inject_playback(name: str) -> bool:
    """VB-Cable 播放设备「CABLE Input」：本机 TTS 注入微信麦克风；对它做回环采不到扬声器里的对端。"""
    n = _norm_audio_device_name(name)
    return "vb-audio" in n and "cable input" in n


def _is_vb_cable_bad_for_remote_capture_input(name: str) -> bool:
    """
    VB-Cable 录音设备（常见为 CABLE Output）：只含播到 CABLE Input 上的信号，即本机送话，不是对方经扬声器出来的声音。
    自动选 PyAudio 输入时应跳过。
    """
    n = _norm_audio_device_name(name)
    if "vb-audio" not in n:
        return False
    return "cable output" in n or "cable input" in n


class AudioCapture:
    """音频捕获器"""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self._running = False
        self._capture_thread = None
        self._audio_queue = queue.Queue()
        self._pyaudio = None
        self._stream = None
        self._input_device_index: Optional[int] = None
        self._input_device_name: Optional[str] = None
        self._asr_auto_device = False
        self._capture_backend: str = "none"  # wasapi_loopback | pyaudio
        self._loopback_mic_name: Optional[str] = None
        # 最近一次 start() 失败原因，供 PhoneAgentManager /status 展示
        self.last_start_error: Optional[str] = None

    def _find_input_by_substr(self, pa: Any, substr: str) -> Optional[int]:
        s = (substr or "").strip().lower()
        if not s:
            return None
        try:
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if int(info.get("maxInputChannels", 0) or 0) < 1:
                    continue
                name = str(info.get("name") or "")
                if s in name.lower():
                    self._input_device_name = name
                    return int(i)
        except Exception as e:
            logger.warning("enumerate input devices failed: %s", e)
        return None

    def _pick_input_device_index(self, pa: Any, substr: str) -> Optional[int]:
        """用户显式指定子串时：匹配失败会打警告。"""
        r = self._find_input_by_substr(pa, substr)
        if r is None and (substr or "").strip():
            logger.warning("No input device contains %r; using default device", substr)
        return r

    def _pick_auto_loopback_device(self, pa: Any) -> Optional[int]:
        """
        未指定设备时：优先选「立体声混音」类设备，才能采到扬声器里对方语音。
        """
        needles = (
            "stereo mix",
            "立体声混音",
            "what u hear",
            "wave out mix",
            "loopback",
            "混音",
            "voicemeeter",
            "voice meeter",
            "aux mix",
        )
        for needle in needles:
            idx = self._find_input_by_substr(pa, needle)
            if idx is not None:
                nm = self._input_device_name or ""
                if _is_vb_cable_bad_for_remote_capture_input(nm):
                    logger.info(
                        "Phone ASR: skip input matched by %r -> %r (VB-Cable line, not remote party)",
                        needle,
                        nm,
                    )
                    continue
                logger.info(
                    "Phone ASR: auto-selected input for remote audio (needle=%r) -> %s",
                    needle,
                    self._input_device_name,
                )
                self._asr_auto_device = True
                return idx
        return None

    def _should_try_wasapi_loopback(self) -> bool:
        if sys.platform != "win32":
            return False
        if not SOUNDCARD_AVAILABLE or not NUMPY_AVAILABLE:
            return False
        if _env_bool("XCAGI_PHONE_LOOPBACK", True) is False:
            return False
        if _env_bool("XCAGI_PHONE_USE_DEFAULT_MIC", False):
            return False
        if (os.environ.get("XCAGI_PHONE_INPUT_DEVICE_SUBSTR") or "").strip():
            return False
        return True

    def _pick_loopback_microphone(self):
        """Windows：与指定/默认扬声器对应的 loopback 麦克风。"""
        assert sc is not None
        substr = (os.environ.get("XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR") or "").strip().lower()
        if substr:
            for speaker in sc.all_speakers():
                if substr not in speaker.name.lower():
                    continue
                if _is_vb_cable_tts_inject_playback(speaker.name):
                    logger.warning(
                        "Phone ASR: LOOPBACK_SPEAKER_SUBSTR 匹配到 VB-Cable CABLE Input（仅本机 TTS），"
                        "无法采扬声器对端，跳过该扬声器"
                    )
                    continue
                mic = sc.get_microphone(speaker.name, include_loopback=True)
                logger.info(
                    "Phone ASR: loopback for speaker substr=%r -> %s",
                    substr,
                    mic.name,
                )
                return mic
            logger.warning(
                "XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR=%r matched no speaker; using default speaker loopback",
                substr,
            )
        sp = sc.default_speaker()
        if _is_vb_cable_tts_inject_playback(sp.name):
            logger.warning(
                "Phone ASR: 系统默认播放设备为 VB-Cable「CABLE Input」（送微信 TTS 的线），"
                "对它回环只能采到合成音。将改用其它物理扬声器做 WASAPI 回环以采对端。"
            )
            alt = None
            for speaker in sc.all_speakers():
                if _is_vb_cable_tts_inject_playback(speaker.name):
                    continue
                alt = speaker
                break
            if alt is not None:
                sp = alt
                logger.info("Phone ASR: WASAPI loopback 改用扬声器 -> %r", sp.name)
            else:
                logger.warning(
                    "Phone ASR: 仅检测到 VB-Cable 扬声器，回环仍可能只含 TTS；"
                    "请在 Windows 声音中保留耳机/扬声器为默认播放，或设置 XCAGI_PHONE_LOOPBACK_SPEAKER_SUBSTR"
                )
        mic = sc.get_microphone(sp.name, include_loopback=True)
        logger.info("Phone ASR: WASAPI loopback from default speaker %r -> mic %r", sp.name, mic.name)
        return mic

    def _float_stereo_to_pcm16_mono(self, data) -> bytes:
        """SoundCard float32 [-1,1]，Windows 用双声道 downmix 再转 s16le（单声道 WASAPI 在部分机器上会坏数据）。"""
        if not NUMPY_AVAILABLE:
            return b""
        if data is None or (hasattr(data, "size") and data.size == 0):
            return b""
        arr = np.asarray(data, dtype=np.float32)
        if arr.ndim == 2:
            mono = np.mean(arr, axis=1)
        else:
            mono = arr
        mono = np.clip(mono, -1.0, 1.0)
        pcm = (mono * 32767.0).astype(np.int16)
        return pcm.tobytes()

    def _loopback_capture_loop(self, mic) -> None:
        rates = list(dict.fromkeys([48000, 44100, int(self.sample_rate) if self.sample_rate else 48000]))
        last_err: Optional[Exception] = None
        rec = None
        for rate in rates:
            rec = None
            try:
                # Windows：必须 channels>=2，单声道可能为垃圾数据（SoundCard 文档）
                rec = mic.recorder(samplerate=rate, channels=2)
                self.sample_rate = rate
                self._loopback_mic_name = getattr(mic, "name", None)
                logger.info("Phone ASR: loopback recorder opened at %s Hz (stereo->mono)", rate)
                try:
                    while self._running:
                        try:
                            data = rec.record(numframes=self.chunk_size)
                            pcm = self._float_stereo_to_pcm16_mono(data)
                            if pcm:
                                self._audio_queue.put(pcm)
                        except Exception as e:
                            logger.debug("Phone ASR: record chunk error: %s", e)
                            time.sleep(0.01)
                finally:
                    # 必须先关闭 Recorder，再在上层 CoUninitialize；否则 WASAPI/COM 易堆损坏
                    if rec is not None:
                        try:
                            rec.close()
                        except Exception:
                            pass
                        rec = None
                return
            except Exception as e:
                last_err = e
                logger.warning("Phone ASR: loopback at %s Hz failed: %s", rate, e)
                if rec is not None:
                    try:
                        rec.close()
                    except Exception:
                        pass
                    rec = None
        logger.error("Phone ASR: loopback capture failed: %s", last_err)
        self._running = False

    def _loopback_worker(self) -> None:
        """
        soundcard/WASAPI 依赖 COM。Flask 等工作线程里若未初始化公寓，常见 0x800401f0。
        在独立线程内完成：STA CoInit → 选 loopback 麦克风 → 采集循环 → 释放 Recorder → CoUninit。
        """
        com_inited = com_init_apartment_thread()
        if not is_pythoncom_available():
            logger.info(
                "Phone ASR: 未安装 pywin32；若 WASAPI 枚举失败可执行: pip install pywin32"
            )
        mic = None
        try:
            try:
                mic = self._pick_loopback_microphone()
            except Exception as e:
                logger.warning("Phone ASR: pick loopback microphone failed: %s", e)
                return
            self._loopback_capture_loop(mic)
        finally:
            # 确保麦克风资源被释放
            if mic is not None:
                try:
                    if hasattr(mic, "close"):
                        mic.close()
                except Exception:
                    pass
            com_uninit_apartment_thread(com_inited)

    def _capture_loop(self):
        """PyAudio 捕获循环"""
        while self._running and self._stream:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                self._audio_queue.put(data)
            except Exception as e:
                logger.error(f"Capture error: {e}")
                break

    def _start_loopback(self) -> bool:
        if not self._should_try_wasapi_loopback():
            return False

        self._capture_backend = "wasapi_loopback"
        self._running = True
        self._capture_thread = threading.Thread(
            target=self._loopback_worker,
            daemon=True,
        )
        self._capture_thread.start()
        time.sleep(0.55)
        if not self._capture_thread.is_alive():
            logger.warning("Phone ASR: loopback thread exited immediately; falling back to PyAudio if available")
            self.last_start_error = (
                "WASAPI 回环线程立即退出（可尝试：pip install pywin32；"
                "确认默认播放设备为物理扬声器而非仅 VB-Cable；或设 XCAGI_PHONE_USE_DEFAULT_MIC=1 用麦克风试跑）"
            )
            self._running = False
            try:
                self._capture_thread.join(timeout=1.5)
            except Exception:
                pass
            self._capture_thread = None
            self._capture_backend = "none"
            return False
        return True

    def _pick_fallback_if_default_input_is_vb(self, pa: Any) -> Optional[int]:
        """若默认录音是 VB-Cable（只含送微信的 TTS），改用第一个非 VB 的物理输入。"""
        try:
            info = pa.get_default_input_device_info()
            name = str(info.get("name") or "")
            if not _is_vb_cable_bad_for_remote_capture_input(name):
                return None
        except Exception:
            return None
        logger.warning(
            "Phone ASR: 系统默认录音为 VB-Cable（%s），只含本机注入 TTS，不能采对方；正在查找其它录音设备…",
            name,
        )
        try:
            for i in range(pa.get_device_count()):
                inf = pa.get_device_info_by_index(i)
                if int(inf.get("maxInputChannels", 0) or 0) < 1:
                    continue
                nm = str(inf.get("name") or "")
                if _is_vb_cable_bad_for_remote_capture_input(nm):
                    continue
                self._input_device_name = nm
                logger.info("Phone ASR: 已改用录音设备 -> %s", nm)
                return int(i)
        except Exception as e:
            logger.warning("Phone ASR: enumerate inputs for VB fallback failed: %s", e)
        logger.error(
            "Phone ASR: 除 VB-Cable 外未发现可用录音设备；请在「声音 → 录制」将默认麦克风改为物理设备或启用立体声混音"
        )
        return None

    def _start_pyaudio(self) -> bool:
        if not PYAUDIO_AVAILABLE:
            logger.error("Cannot start capture: PyAudio not available")
            return False

        self._pyaudio = pyaudio.PyAudio()
        self._asr_auto_device = False
        substr = (os.environ.get("XCAGI_PHONE_INPUT_DEVICE_SUBSTR") or "").strip()
        use_default_mic = _env_bool("XCAGI_PHONE_USE_DEFAULT_MIC", False)
        if substr:
            self._input_device_index = self._pick_input_device_index(self._pyaudio, substr)
        elif use_default_mic:
            self._input_device_index = None
            self._input_device_name = None
        else:
            self._input_device_index = self._pick_auto_loopback_device(self._pyaudio)
            if self._input_device_index is None:
                logger.warning(
                    "未找到立体声混音/混音类输入：ASR 将用系统默认录音设备，通常只能采麦克风，无法识别通话对端。"
                    "可安装 soundcard 并启用 WASAPI 回环，或在「声音 → 录制」启用立体声混音。"
                )
                self._input_device_name = None

        if not substr and self._input_device_index is None:
            alt = self._pick_fallback_if_default_input_is_vb(self._pyaudio)
            if alt is not None:
                self._input_device_index = alt

        stream_kw = dict(
            format=pyaudio.paInt16,
            channels=self.channels,
            input=True,
            frames_per_buffer=self.chunk_size,
        )
        if self._input_device_index is not None:
            stream_kw["input_device_index"] = self._input_device_index

        base_rate = int(self.sample_rate)
        rates_to_try = list(dict.fromkeys([base_rate, 48000, 44100, 16000]))

        self._stream = None
        last_err: Optional[Exception] = None
        for rate in rates_to_try:
            try:
                kw = dict(stream_kw, rate=rate)
                self._stream = self._pyaudio.open(**kw)
                self.sample_rate = rate
                logger.info("Audio capture stream opened at %s Hz", rate)
                break
            except Exception as e:
                last_err = e
                self._stream = None
        if self._stream is None:
            raise last_err if last_err else RuntimeError("pyaudio.open failed")

        self._capture_backend = "pyaudio"
        self._running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        logger.info(
            "Audio capture started (backend=pyaudio, device=%s, %s Hz)",
            self._input_device_name or "default",
            self.sample_rate,
        )
        return True

    def start(self) -> bool:
        """开始捕获：Windows 优先 WASAPI 扬声器回环，否则 PyAudio。"""
        if self._running:
            logger.warning("Capture already running")
            return True

        self._capture_backend = "none"
        self._loopback_mic_name = None
        self.last_start_error = None

        try:
            if self._start_loopback():
                return True
        except Exception as e:
            self.last_start_error = str(e).strip() or repr(e)
            logger.warning("Phone ASR: loopback start error: %s", e)

        try:
            ok = self._start_pyaudio()
            if ok:
                return True
            self.last_start_error = self.last_start_error or (
                "PyAudio 未能打开输入流（未安装 PyAudio、无可用录音设备，或立体声混音未启用）"
            )
            return False
        except Exception as e:
            msg = str(e).strip() or repr(e)
            self.last_start_error = self.last_start_error or msg
            logger.error(f"Failed to start audio capture: {e}")
            self._cleanup()
            return False

    def stop(self):
        """停止捕获"""
        self._running = False

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=3.0)

        self._cleanup()
        logger.info("Audio capture stopped")

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[bytes]:
        """获取音频块"""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain_chunks(self, max_chunks: int = 64) -> List[bytes]:
        """非阻塞取走队列中已有块（供 RMS 静音分段）。"""
        out: List[bytes] = []
        for _ in range(max(1, max_chunks)):
            try:
                out.append(self._audio_queue.get_nowait())
            except queue.Empty:
                break
        return out

    def discard_queued_chunks(self, max_drain: int = 20000) -> int:
        """丢弃采音队列中尚未被 process_loop 消费的块（新来电/接听/挂断时避免串话）。"""
        n = 0
        for _ in range(max(0, int(max_drain))):
            try:
                self._audio_queue.get_nowait()
                n += 1
            except queue.Empty:
                break
        return n

    def get_capture_backend(self) -> str:
        return self._capture_backend

    def is_capture_thread_alive(self) -> bool:
        """采音线程是否在跑；若已退出则队列不会再有 PCM，RMS 会持续≈0。"""
        t = self._capture_thread
        return t is not None and t.is_alive()

    def get_input_device_label(self) -> str:
        """用于 status：当前输入设备说明。"""
        if self._capture_backend == "wasapi_loopback":
            return self._loopback_mic_name or "WASAPI loopback (默认扬声器)"
        if self._input_device_name:
            return self._input_device_name
        # 勿写英文 Input，易与 VB「CABLE Input」播放端混淆
        return "default（系统默认输入设备）"

    def get_sample_rate(self) -> int:
        return int(self.sample_rate)

    def list_input_devices(self) -> List[dict]:
        """列出 PyAudio 输入设备；若在 Windows 可额外附带扬声器列表供回环选择。"""
        out: List[dict] = []
        if PYAUDIO_AVAILABLE:
            pa = self._pyaudio
            own = False
            if pa is None:
                try:
                    pa = pyaudio.PyAudio()
                    own = True
                except Exception as e:
                    logger.warning("list_input_devices: PyAudio init failed: %s", e)
                    pa = None
            if pa is not None:
                try:
                    for i in range(pa.get_device_count()):
                        info = pa.get_device_info_by_index(i)
                        if int(info.get("maxInputChannels", 0) or 0) < 1:
                            continue
                        out.append({"index": int(i), "name": str(info.get("name") or "")})
                except Exception as e:
                    logger.warning("list_input_devices: enumerate failed: %s", e)
                finally:
                    if own and pa is not None:
                        try:
                            pa.terminate()
                        except Exception:
                            pass
        if sys.platform == "win32" and SOUNDCARD_AVAILABLE and sc is not None:
            try:
                for speaker in list(sc.all_speakers())[:16]:
                    out.append(
                        {
                            "index": -1,
                            "name": f"[扬声器·回环] {speaker.name}",
                            "kind": "speaker_loopback_hint",
                        }
                    )
            except Exception:
                pass
        return out

    def is_available(self) -> bool:
        """PyAudio 或（Windows 下）SoundCard+numpy 任一可用即可启动采集。"""
        if PYAUDIO_AVAILABLE:
            return True
        if sys.platform == "win32" and SOUNDCARD_AVAILABLE and NUMPY_AVAILABLE:
            return True
        return False

    def _cleanup(self):
        """清理资源"""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except Exception:
                break
