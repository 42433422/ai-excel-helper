"""
ASR 语音转文字

优先使用 faster-whisper（CTranslate2）：同尺寸模型通常比 openai-whisper 更快，CPU 上 int8 量化明显省时间。
未安装 faster-whisper 时回退 openai-whisper。

环境变量：
  XCAGI_PHONE_WHISPER_BACKEND   auto | faster | openai（默认 auto：有 faster 则用）
  XCAGI_PHONE_WHISPER_MODEL     模型名，默认 small（中英电话场景折中）；要快可 tiny，要更准可 medium
  XCAGI_PHONE_WHISPER_DEVICE    cuda | cpu（空则自动）
  XCAGI_PHONE_WHISPER_COMPUTE_TYPE  faster 专用：cpu 常用 int8；cuda 常用 float16（空则自动）
  XCAGI_PHONE_WHISPER_BEAM      beam 宽度，默认 5（准）；设 1 最快
  XCAGI_PHONE_WHISPER_VAD       1 时 faster-whisper 内部 VAD（我们已分段，默认 0 避免误切）
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "small"

try:
    import whisper as openai_whisper

    OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    OPENAI_WHISPER_AVAILABLE = False
    openai_whisper = None  # type: ignore
    logger.debug("openai-whisper not installed; ASR will use faster-whisper only if available")

try:
    from faster_whisper import WhisperModel as FasterWhisperModel

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    FasterWhisperModel = None  # type: ignore
    logger.debug("faster-whisper not installed; pip install faster-whisper for faster ASR")


def _env_backend() -> str:
    v = (os.environ.get("XCAGI_PHONE_WHISPER_BACKEND") or "auto").strip().lower()
    return v if v in ("auto", "faster", "openai") else "auto"


def _infer_device() -> str:
    d = (os.environ.get("XCAGI_PHONE_WHISPER_DEVICE") or "").strip().lower()
    if d in ("cuda", "cpu"):
        return d
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _infer_compute_type(device: str) -> str:
    ct = (os.environ.get("XCAGI_PHONE_WHISPER_COMPUTE_TYPE") or "").strip().lower()
    if ct:
        return ct
    return "float16" if device == "cuda" else "int8"


def _beam_size() -> int:
    try:
        return max(1, int(os.environ.get("XCAGI_PHONE_WHISPER_BEAM", "5")))
    except ValueError:
        return 5


def _vad_filter() -> bool:
    return (os.environ.get("XCAGI_PHONE_WHISPER_VAD") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class ASRProcessor:
    """ASR：优先 faster-whisper，其次 openai-whisper"""

    def __init__(self, model_size: Optional[str] = None):
        raw = (model_size or os.environ.get("XCAGI_PHONE_WHISPER_MODEL") or "").strip()
        self.model_size = raw if raw else _DEFAULT_MODEL
        self._backend: str = "none"
        self._model: Any = None
        self._device: Optional[str] = None
        self._compute_type: Optional[str] = None
        self._load_model()

    def _load_model(self) -> None:
        backend = _env_backend()
        want_faster = backend in ("auto", "faster")
        if backend == "faster" and not FASTER_WHISPER_AVAILABLE:
            logger.error("XCAGI_PHONE_WHISPER_BACKEND=faster 但未安装 faster-whisper（pip install faster-whisper）")

        if want_faster and FASTER_WHISPER_AVAILABLE and FasterWhisperModel is not None:
            try:
                self._load_faster()
                self._backend = "faster"
                logger.info(
                    "[ASR] faster-whisper 已加载 model=%s device=%s compute_type=%s",
                    self.model_size,
                    self._device,
                    self._compute_type,
                )
                return
            except Exception as e:
                logger.warning("[ASR] faster-whisper 加载失败，尝试 openai-whisper: %s", e)

        if backend == "faster":
            self._model = None
            self._backend = "none"
            return

        if OPENAI_WHISPER_AVAILABLE and openai_whisper is not None:
            try:
                logger.info("[ASR] 加载 openai-whisper model=%s", self.model_size)
                self._model = openai_whisper.load_model(self.model_size)
                self._backend = "openai"
                logger.info("[ASR] openai-whisper 加载成功")
                return
            except Exception as e:
                logger.error("[ASR] openai-whisper 加载失败: %s", e)

        self._model = None
        self._backend = "none"

    def _load_faster(self) -> None:
        assert FasterWhisperModel is not None
        device = _infer_device()
        compute_type = _infer_compute_type(device)
        self._device = device
        self._compute_type = compute_type
        self._model = FasterWhisperModel(
            self.model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(self, audio_path: str) -> Optional[str]:
        if not self._model:
            logger.warning("ASR model not available")
            return None
        if self._backend == "faster":
            return self._transcribe_faster(audio_path)
        if self._backend == "openai":
            return self._transcribe_openai(audio_path)
        return None

    def _transcribe_faster(self, audio_path: str) -> Optional[str]:
        try:
            beam = _beam_size()
            vad = _vad_filter()
            segments, _info = self._model.transcribe(
                audio_path,
                language="zh",
                beam_size=beam,
                vad_filter=vad,
            )
            text = "".join(s.text for s in segments).strip()
            logger.info("[ASR] faster-whisper: %s", text[:200] + ("…" if len(text) > 200 else ""))
            return text or None
        except Exception as e:
            logger.error("[ASR] faster-whisper transcribe failed: %s", e)
            return None

    def _transcribe_openai(self, audio_path: str) -> Optional[str]:
        try:
            beam = _beam_size()
            result = self._model.transcribe(
                audio_path,
                language="zh",
                fp16=False,
                beam_size=beam,
            )
            text = result.get("text", "").strip()
            logger.info("[ASR] openai-whisper: %s", text[:200] + ("…" if len(text) > 200 else ""))
            return text or None
        except TypeError:
            # 旧版 openai-whisper 无 beam_size
            try:
                result = self._model.transcribe(audio_path, language="zh", fp16=False)
                text = result.get("text", "").strip()
                return text or None
            except Exception as e2:
                logger.error("[ASR] openai-whisper transcribe failed: %s", e2)
                return None
        except Exception as e:
            logger.error("[ASR] openai-whisper transcribe failed: %s", e)
            return None

    def transcribe_from_bytes(self, audio_data: bytes) -> Optional[str]:
        logger.warning("transcribe_from_bytes not implemented yet")
        return None

    @property
    def backend_kind(self) -> str:
        return self._backend

    @property
    def device_label(self) -> Optional[str]:
        return self._device

    @property
    def compute_type_label(self) -> Optional[str]:
        return self._compute_type

    def is_available(self) -> bool:
        return self._model is not None
