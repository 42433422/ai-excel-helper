# -*- coding: utf-8 -*-
"""
PaddleOCR 单例与统一解析：供 OCRService 与标签识别模板共用。

本地模型（离线）环境变量：

- **XCAGI_PADDLE_MODEL_ROOT**：目录下需含 PaddleX 推理包（带 ``inference.yml``）：
  ``PP-OCRv4_mobile_det_infer``、``PP-OCRv4_mobile_rec_infer``
  （请运行 ``scripts/download_paddleocr_ch_models.py`` 从百度 BOS 拉取）

或分别指定（优先级高于 XCAGI_PADDLE_MODEL_ROOT）：

- **PADDLEOCR_TEXT_DET_MODEL_DIR** / **PADDLEOCR_TEXT_REC_MODEL_DIR**
- **PADDLEOCR_TEXT_DET_MODEL_NAME** / **PADDLEOCR_TEXT_REC_MODEL_NAME**（需与目录内 ``inference.yml`` 中 ``Global.model_name`` 一致，默认分别为 ``PP-OCRv4_mobile_det`` / ``PP-OCRv4_mobile_rec``）

本地模式下会关闭文档预处理与文字行方向模型，避免额外联网下载。

未配置本地目录时仍按 ``lang`` 在线拉取；内网失败时可设 ``PADDLE_PDX_MODEL_SOURCE=BOS`` 走百度 BOS 源。
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_paddle_ocr = None  # type: ignore


def check_paddle_available() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except ImportError:
        return False


def _is_paddlex_infer_dir(path: str) -> bool:
    return bool(path) and os.path.isfile(os.path.join(path, "inference.yml"))


def _pick_det_rec_dirs(root: str) -> Tuple[Optional[str], Optional[str]]:
    """在 root 下查找含 inference.yml 的 det/rec 目录（优先 PaddleX 官方目录名）。"""
    det_candidates = (
        "PP-OCRv4_mobile_det_infer",
        "ch_PP-OCRv4_det_infer",
    )
    rec_candidates = (
        "PP-OCRv4_mobile_rec_infer",
        "ch_PP-OCRv4_rec_infer",
    )
    det = next((os.path.join(root, n) for n in det_candidates if _is_paddlex_infer_dir(os.path.join(root, n))), None)
    rec = next((os.path.join(root, n) for n in rec_candidates if _is_paddlex_infer_dir(os.path.join(root, n))), None)
    return det, rec


def _resolve_local_model_dirs() -> Tuple[Optional[str], Optional[str]]:
    """返回 (det_dir, rec_dir)，均为 PaddleX 格式目录。"""
    det = os.environ.get("PADDLEOCR_TEXT_DET_MODEL_DIR", "").strip()
    rec = os.environ.get("PADDLEOCR_TEXT_REC_MODEL_DIR", "").strip()

    root = os.environ.get("XCAGI_PADDLE_MODEL_ROOT", "").strip()
    if root:
        root = os.path.abspath(root)
        if not det or not rec:
            rd, rr = _pick_det_rec_dirs(root)
            det = det or (rd or "")
            rec = rec or (rr or "")

    det = det or None
    rec = rec or None
    return det, rec


def _resolve_local_model_names(det_dir: Optional[str], rec_dir: Optional[str]) -> Tuple[str, str]:
    """与 inference.yml 中 Global.model_name 一致；可通过环境变量覆盖。"""
    dname = os.environ.get("PADDLEOCR_TEXT_DET_MODEL_NAME", "").strip()
    rname = os.environ.get("PADDLEOCR_TEXT_REC_MODEL_NAME", "").strip()
    if dname and rname:
        return dname, rname
    # 默认与 download_paddleocr_ch_models.py 下载的 PP-OCRv4 mobile 包一致
    return "PP-OCRv4_mobile_det", "PP-OCRv4_mobile_rec"


def get_paddle_ocr_instance():
    """懒加载 PaddleOCR（全进程共享一份，降低显存/内存占用）。"""
    global _paddle_ocr
    with _lock:
        if _paddle_ocr is None:
            from paddleocr import PaddleOCR

            lang = os.environ.get("PADDLEOCR_LANG", "ch").strip() or "ch"
            det_dir, rec_dir = _resolve_local_model_dirs()

            if det_dir and rec_dir:
                dn, rn = _resolve_local_model_names(det_dir, rec_dir)
                kw: Dict[str, Any] = {
                    "text_detection_model_name": dn,
                    "text_detection_model_dir": det_dir,
                    "text_recognition_model_name": rn,
                    "text_recognition_model_dir": rec_dir,
                    "use_doc_orientation_classify": False,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": False,
                }
                _paddle_ocr = PaddleOCR(**kw)
                logger.info(
                    "PaddleOCR 初始化成功（本地模型 det=%s rec=%s）",
                    det_dir,
                    rec_dir,
                )
            else:
                if root_hint := os.environ.get("XCAGI_PADDLE_MODEL_ROOT", "").strip():
                    logger.warning(
                        "已设置 XCAGI_PADDLE_MODEL_ROOT=%s 但未找到完整 det/rec 推理目录，将回退在线拉模。请运行 scripts/download_paddleocr_ch_models.py",
                        root_hint,
                    )
                _paddle_ocr = PaddleOCR(lang=lang)
                logger.info("PaddleOCR 初始化成功 (lang=%s, 在线模型)", lang)
        return _paddle_ocr


def _normalize_predict_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, list) and len(result) > 0:
        result = result[0]
    if hasattr(result, "json"):
        json_result = result.json
    elif isinstance(result, dict):
        json_result = result
    else:
        json_result = {}
    if not isinstance(json_result, dict):
        return {}
    res_data = json_result.get("res", {})
    return res_data if isinstance(res_data, dict) else {}


def predict_to_text_blocks(image_array: np.ndarray) -> List[Dict[str, Any]]:
    """
    对 RGB numpy 图像执行 Paddle predict，返回与标签模板一致的 text_blocks 结构。
    """
    ocr = get_paddle_ocr_instance()
    with _lock:
        raw = ocr.predict(image_array)
    res_data = _normalize_predict_result(raw)
    rec_texts = res_data.get("rec_texts", []) or []
    rec_scores = res_data.get("rec_scores", []) or []
    rec_polys = res_data.get("rec_polys", []) or []

    text_blocks: List[Dict[str, Any]] = []
    for i, text in enumerate(rec_texts):
        text = (text or "").strip()
        if not text:
            continue
        if i >= len(rec_polys) or not rec_polys[i]:
            continue
        bbox = rec_polys[i]
        center_x = sum(float(p[0]) for p in bbox) / len(bbox)
        center_y = sum(float(p[1]) for p in bbox) / len(bbox)
        score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        text_blocks.append(
            {
                "text": text,
                "left": int(min(xs)),
                "top": int(min(ys)),
                "width": int(max(xs) - min(xs)),
                "height": int(max(ys) - min(ys)),
                "conf": score * 100.0,
                "center": (center_x, center_y),
                "y_center": center_y,
            }
        )
    return text_blocks


