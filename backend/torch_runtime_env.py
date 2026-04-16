"""
Import-time environment for torch / sentence-transformers heavy paths.

``http_app`` imports this module before other backend code so tokenizer and
torch subprocess behavior stays predictable in uvicorn workers.
"""

from __future__ import annotations

import logging
import os


def apply_sentence_transformers_compat_env() -> None:
    """Set defaults that avoid common tokenizer / HF foot-guns in web workers."""
    # Avoid "The current process just got forked..." spam when HF tokenizers use threads.
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def suppress_torch_elastic_redirect_notes() -> None:
    """Quiet torch.distributed.elastic chatter when only inference libs are on the path."""
    try:
        for name in (
            "torch.distributed.elastic",
            "torch.distributed.elastic.agent",
            "torch.distributed",
        ):
            logging.getLogger(name).setLevel(logging.WARNING)
    except Exception:
        pass
