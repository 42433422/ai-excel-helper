"""
在首次加载 sentence-transformers / torch 之前统一环境变量与日志级别。

缓解 Windows 上 ``torch.distributed.elastic`` 的 Redirects 提示，以及
tokenizers 多进程与 OMP 冲突导致的异常弹窗（「无法找到入口」等）。
"""

from __future__ import annotations

import logging
import os
import warnings

_env_applied = False
_warn_applied = False


def apply_sentence_transformers_compat_env() -> None:
    """幂等：在 ``import sentence_transformers`` / ``torch`` 之前调用。"""
    global _env_applied
    if _env_applied:
        return
    _env_applied = True
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_MAX_THREADS", "1")


def suppress_torch_elastic_redirect_notes() -> None:
    """降低 torch.distributed.elastic 相关 WARNING（含 Redirects 不支持 Windows 的说明）。"""
    global _warn_applied
    if _warn_applied:
        return
    _warn_applied = True
    for name in (
        "torch.distributed.elastic.multiprocessing.redirects",
        "torch.distributed.elastic.multiprocessing",
        "torch.distributed.elastic",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message=".*Redirects are currently not supported.*")
