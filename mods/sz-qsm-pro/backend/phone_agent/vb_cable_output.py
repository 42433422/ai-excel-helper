"""
VB-Cable 虚拟麦克风输出模块
功能：将音频输出到 VB-Cable 虚拟麦克风

注意：Edge TTS 返回的是 MP3（audio/mpeg），而 PyAudio 流需要 s16le PCM。
若直接把 MP3 字节 write 进流，对端听不到正常语音。
"""

import io
import logging
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_ffmpeg_executable() -> Optional[str]:
    """
    优先 PATH 中的 ffmpeg；否则尝试 imageio_ffmpeg 自带的 ffmpeg（无需用户单独安装）。
    """
    w = shutil.which("ffmpeg")
    if w:
        return w
    try:
        import imageio_ffmpeg  # type: ignore

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception as e:
        logger.debug("imageio_ffmpeg not available: %s", e)
    return None


def miniaudio_available() -> bool:
    """不依赖 ffmpeg：用 miniaudio（dr_mp3）解码 Edge-TTS 的 MP3。"""
    try:
        import miniaudio  # noqa: F401

        return True
    except ImportError:
        return False


def mp3_decode_tooling_available() -> bool:
    """任一路径可解码 MP3 即视为可用（供 /status）。"""
    return bool(resolve_ffmpeg_executable()) or miniaudio_available()


try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available, VB-Cable output disabled")


class VBCableOutput:
    """VB-Cable 输出器"""

    VB_CABLE_DEVICE_NAME = "CABLE Input"
    # 优先按设备 defaultSampleRate 打开（多为 44100/48000）；固定 16kHz 在部分 Win+PyAudio 下会无声或异常
    _FALLBACK_SAMPLE_RATES = (48000, 44100, 16000, 22050, 32000)

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._running = False
        self._playback_thread = None
        self._audio_queue = queue.Queue()
        self._pyaudio = None
        self._stream = None
        self._vb_cable_device_index = None
        self._vb_cable_device_name = None

    def start(self) -> bool:
        """开始输出"""
        if not PYAUDIO_AVAILABLE:
            logger.error("Cannot start VB-Cable output: PyAudio not available")
            return False

        if self._running:
            logger.warning("VB-Cable output already running")
            return True

        try:
            self._pyaudio = pyaudio.PyAudio()
            self._vb_cable_device_index = self._find_vb_cable_device()

            if self._vb_cable_device_index is None:
                logger.error("VB-Cable device not found")
                self._pyaudio.terminate()
                return False

            rates = self._playback_sample_rates_to_try()
            last_err: Optional[Exception] = None
            self._stream = None
            for rate in rates:
                try:
                    self.sample_rate = rate
                    self._stream = self._pyaudio.open(
                        format=pyaudio.paInt16,
                        channels=self.channels,
                        rate=self.sample_rate,
                        output=True,
                        output_device_index=self._vb_cable_device_index,
                    )
                    logger.info(
                        "VB-Cable stream opened: %s Hz mono (device index %s)",
                        self.sample_rate,
                        self._vb_cable_device_index,
                    )
                    break
                except Exception as e:
                    last_err = e
                    logger.warning("VB-Cable open failed at %s Hz: %s", rate, e)
            if self._stream is None:
                logger.error("VB-Cable: could not open output stream: %s", last_err)
                self._cleanup()
                return False

            self._running = True
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()

            ff = resolve_ffmpeg_executable()
            ma = miniaudio_available()
            logger.info(
                "VB-Cable output started; MP3 decode ffmpeg=%s miniaudio=%s",
                ff or "(无)",
                "yes" if ma else "no (pip install miniaudio 可无 ffmpeg 解码)",
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start VB-Cable output: {e}")
            self._cleanup()
            return False

    def _playback_sample_rates_to_try(self) -> list:
        """先设备默认采样率，再常见档位，避免 16k 与驱动不兼容导致无声。"""
        out: list = []
        try:
            if self._pyaudio is not None and self._vb_cable_device_index is not None:
                info = self._pyaudio.get_device_info_by_index(self._vb_cable_device_index)
                native = int(round(float(info.get("defaultSampleRate", 48000))))
                if 4000 <= native <= 192000:
                    out.append(native)
        except Exception as e:
            logger.debug("VB-Cable defaultSampleRate read failed: %s", e)
        for r in self._FALLBACK_SAMPLE_RATES:
            if r not in out:
                out.append(r)
        return out

    def stop(self):
        """停止输出"""
        self._running = False

        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=2.0)

        self._cleanup()
        logger.info("VB-Cable output stopped")

    def _find_vb_cable_device(self, pyaudio_instance=None) -> Optional[int]:
        """查找 VB-Cable 设备"""
        pa = pyaudio_instance or self._pyaudio
        if not pa:
            return None

        try:
            device_count = pa.get_device_count()
            for i in range(device_count):
                device_info = pa.get_device_info_by_index(i)
                device_name = device_info.get("name", "")
                if self.VB_CABLE_DEVICE_NAME in device_name:
                    logger.info(f"Found VB-Cable device: {device_name} (index: {i})")
                    self._vb_cable_device_name = device_name
                    return i

            logger.warning("VB-Cable device not found in audio devices")
            return None

        except Exception as e:
            logger.error(f"Failed to find VB-Cable device: {e}")
            return None

    def _playback_loop(self):
        """播放循环（分块 write，避免部分驱动对大缓冲一次写入无声）。"""
        frame_bytes = 2 * self.channels
        chunk_bytes = 4096 * frame_bytes
        while self._running and self._stream:
            try:
                audio_data = self._audio_queue.get(timeout=0.1)
                if audio_data:
                    off = 0
                    n = len(audio_data)
                    while off < n:
                        end = min(off + chunk_bytes, n)
                        self._stream.write(audio_data[off:end])
                        off = end
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback error: {e}")
                break

    def _ffmpeg_mp3_to_pcm(self, ffmpeg_exe: str, mp3_bytes: bytes) -> Optional[bytes]:
        """ffmpeg：MP3 → s16le mono @ self.sample_rate。先 pipe，失败再临时文件（Windows 上 pipe 更常失败）。"""
        ar = str(self.sample_rate)
        common_out = [
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            ar,
            "pipe:1",
        ]
        # 显式 -f mp3，避免部分环境下 stdin 探测失败
        pipe_cmd = [
            ffmpeg_exe,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "mp3",
            "-i",
            "pipe:0",
            *common_out,
        ]
        try:
            r = subprocess.run(
                pipe_cmd,
                input=mp3_bytes,
                capture_output=True,
                timeout=120,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
            err = (r.stderr or b"").decode("utf-8", errors="replace")[:500]
            logger.warning("ffmpeg pipe mp3->pcm rc=%s err=%s", r.returncode, err)
        except Exception as e:
            logger.warning("ffmpeg pipe decode exception: %s", e)

        path = None
        fd = -1
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.write(fd, mp3_bytes)
            os.close(fd)
            fd = -1
            file_cmd = [
                ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                path,
                *common_out,
            ]
            r = subprocess.run(
                file_cmd,
                capture_output=True,
                timeout=120,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
            err = (r.stderr or b"").decode("utf-8", errors="replace")[:500]
            logger.warning("ffmpeg file mp3->pcm rc=%s err=%s", r.returncode, err)
        except Exception as e:
            logger.warning("ffmpeg file decode exception: %s", e)
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        return None

    def _mp3_to_pcm_s16le_mono(self, mp3_bytes: bytes) -> Optional[bytes]:
        """将 MP3 转为当前流采样率单声道 s16le PCM（与 PyAudio paInt16 一致）。"""
        if not mp3_bytes:
            return None
        ffmpeg = resolve_ffmpeg_executable()
        if ffmpeg:
            pcm = self._ffmpeg_mp3_to_pcm(ffmpeg, mp3_bytes)
            if pcm:
                return pcm
        try:
            from pydub import AudioSegment

            seg = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
            seg = seg.set_frame_rate(self.sample_rate).set_channels(self.channels).set_sample_width(2)
            return seg.raw_data
        except Exception as e:
            logger.warning("pydub mp3 decode failed: %s", e)
        # pydub 读 MP3 通常仍依赖 ffmpeg；再试临时文件（ffmpeg 与上文同源）
        if ffmpeg:
            try:
                from pydub import AudioSegment

                fd, path = tempfile.mkstemp(suffix=".mp3")
                try:
                    os.write(fd, mp3_bytes)
                    os.close(fd)
                    fd = -1
                    seg = AudioSegment.from_file(path, format="mp3")
                    seg = seg.set_frame_rate(self.sample_rate).set_channels(self.channels).set_sample_width(2)
                    return seg.raw_data
                finally:
                    if fd >= 0:
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            except Exception as e:
                logger.warning("pydub temp file mp3 failed: %s", e)
        pcm_ma = self._try_miniaudio_decode_mp3(mp3_bytes)
        if pcm_ma:
            return pcm_ma
        return None

    def _try_miniaudio_decode_mp3(self, mp3_bytes: bytes) -> Optional[bytes]:
        """无 ffmpeg 时用 miniaudio 解码 MP3 → s16le mono @ self.sample_rate（内置 dr_mp3）。"""
        try:
            import miniaudio
        except ImportError:
            return None
        if not mp3_bytes:
            return None
        path = None
        fd = -1
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.write(fd, mp3_bytes)
            os.close(fd)
            fd = -1
            dec = miniaudio.decode_file(
                path,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=self.channels,
                sample_rate=self.sample_rate,
            )
            samples = dec.samples
            if isinstance(samples, memoryview):
                return samples.tobytes()
            if hasattr(samples, "tobytes"):
                return samples.tobytes()
            return bytes(samples)
        except Exception as e:
            logger.warning("miniaudio mp3 decode failed: %s", e)
            return None
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def play_audio(self, audio_data: bytes) -> bool:
        """
        播放音频。TTS 通常为 MP3，会先解码为 PCM 再写入 VB-Cable。
        若已是 WAV/PCM，可后续再扩展识别。
        返回是否已成功入队。
        """
        if not audio_data:
            return False
        pcm: Optional[bytes]
        if audio_data[:4] == b"RIFF":
            try:
                import wave

                with wave.open(io.BytesIO(audio_data), "rb") as wf:
                    if wf.getnchannels() != self.channels or wf.getframerate() != self.sample_rate:
                        logger.warning(
                            "WAV format mismatch (got %sch %sHz), VB-Cable expects mono %sHz",
                            wf.getnchannels(),
                            wf.getframerate(),
                            self.sample_rate,
                        )
                    pcm = wf.readframes(wf.getnframes())
            except Exception as e:
                logger.warning("WAV parse failed, try as mp3: %s", e)
                pcm = self._mp3_to_pcm_s16le_mono(audio_data)
        else:
            pcm = self._mp3_to_pcm_s16le_mono(audio_data)
        if not pcm:
            logger.error(
                "VB-Cable: 无法将音频解码为 PCM；请 pip install miniaudio（可无 ffmpeg）或安装 ffmpeg / imageio-ffmpeg"
            )
            return False
        self._audio_queue.put(pcm)
        return True

    def discard_pending_playback(self, max_drain: int = 20000) -> int:
        """丢弃尚未写入声卡的 PCM 队列（新来电/接听前清掉上一通未播完的 TTS）。"""
        n = 0
        for _ in range(max(0, int(max_drain))):
            try:
                self._audio_queue.get_nowait()
                n += 1
            except queue.Empty:
                break
        return n

    def get_playback_device_name(self) -> Optional[str]:
        """当前写入 TTS 的播放端设备名（通常为 CABLE Input）；供 status 展示。"""
        return self._vb_cable_device_name

    def get_stream_sample_rate(self) -> Optional[int]:
        """当前 PyAudio 输出流采样率（与解码一致）；未启动则为 None。"""
        if self._running and self._stream is not None:
            return int(self.sample_rate)
        return None

    def is_available(self) -> bool:
        """检查是否可用"""
        if not PYAUDIO_AVAILABLE:
            return False
        
        # 如果已经找到设备，直接返回 True
        if self._vb_cable_device_index is not None:
            return True
        
        # 否则尝试查找设备
        try:
            p = pyaudio.PyAudio()
            device_index = self._find_vb_cable_device(p)
            p.terminate()
            return device_index is not None
        except:
            return False

    def _cleanup(self):
        """清理资源"""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
            self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except:
                pass
            self._pyaudio = None

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except:
                break
