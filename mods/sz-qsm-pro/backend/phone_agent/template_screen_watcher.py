"""
全屏模板匹配：使用 Mod 根目录下的 image.png 作为「微信语音来电条」参考图，
在屏幕截图中定位弹窗后，按模板相对坐标点击绿色接听钮。

依赖（可选）：opencv-python-headless、numpy、Pillow
未安装时本模块自动禁用，不影响 Win32 窗口路径。
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_last_template_click_at: float = 0.0
_cooldown_sec = 2.5
_warned_missing_deps = False
_warned_missing_file = False

# 模板匹配到「接听」绿钮：相对模板左上角的归一化位置（与你提供的窄条 UI 一致）
GREEN_BTN_REL_X = 0.86
GREEN_BTN_REL_Y = 0.72
MATCH_THRESHOLD = 0.72


def _mod_root() -> Path:
    """sz-qsm-pro/backend/phone_agent -> sz-qsm-pro"""
    return Path(__file__).resolve().parent.parent.parent


def template_image_path() -> Path:
    return _mod_root() / "image.png"


def is_template_file_present() -> bool:
    p = template_image_path()
    return p.is_file() and p.stat().st_size > 100


def _lazy_cv2_numpy_pil():
    try:
        import cv2  # noqa: F401
        import numpy as np  # noqa: F401
        from PIL import ImageGrab  # noqa: F401
        return True
    except ImportError:
        return False


def is_runtime_ready() -> bool:
    return _lazy_cv2_numpy_pil()


def is_available() -> bool:
    return is_template_file_present() and is_runtime_ready()


def try_match_template_and_click_answer() -> Optional[Dict[str, Any]]:
    """
    截取主屏区域，与 image.png 做模板匹配；成功则点击绿钮位置。
    冷却时间内不重复点击。
    返回：未点击/未匹配 -> None；已点击 -> 含坐标与分数的字典，供上层展示「识别/点击」步骤。
    """
    global _last_template_click_at, _warned_missing_deps, _warned_missing_file

    if not is_template_file_present():
        if not _warned_missing_file:
            logger.info(
                "[template] 未找到 %s，请将微信来电条截图保存为 image.png 放在本 Mod 根目录",
                template_image_path(),
            )
            _warned_missing_file = True
        return None

    if not is_runtime_ready():
        if not _warned_missing_deps:
            logger.warning(
                "[template] 未安装 opencv-python-headless / numpy / Pillow，跳过屏幕模板接听。"
                " 可执行: pip install opencv-python-headless numpy Pillow"
            )
            _warned_missing_deps = True
        return None

    now = time.time()
    if now - _last_template_click_at < _cooldown_sec:
        return None

    import cv2
    import numpy as np
    from PIL import ImageGrab

    try:
        import win32api
        import win32con
    except ImportError:
        return None

    path = str(template_image_path())
    tmpl = cv2.imread(path)
    if tmpl is None or tmpl.size == 0:
        logger.error("[template] 无法读取模板: %s", path)
        return None

    th, tw = tmpl.shape[:2]

    # 全屏截图（多显示器时尽量整幅虚拟桌面）
    try:
        shot = np.array(ImageGrab.grab(all_screens=True))
    except TypeError:
        shot = np.array(ImageGrab.grab())
    if shot.ndim != 3 or shot.shape[2] < 3:
        return None
    screen_bgr = cv2.cvtColor(shot, cv2.COLOR_RGB2BGR)

    if screen_bgr.shape[0] < th or screen_bgr.shape[1] < tw:
        return None

    res = cv2.matchTemplate(screen_bgr, tmpl, cv2.TM_CCOEFF_NORMED)
    _min_v, max_v, _min_loc, max_loc = cv2.minMaxLoc(res)
    if max_v < MATCH_THRESHOLD:
        logger.debug("[template] 未匹配到来电条 (best=%.3f < %.2f)", max_v, MATCH_THRESHOLD)
        return None

    left, top = int(max_loc[0]), int(max_loc[1])
    gx = left + int(tw * GREEN_BTN_REL_X)
    gy = top + int(th * GREEN_BTN_REL_Y)

    logger.info(
        "[template] 匹配到来电条 score=%.3f 模板左上=(%s,%s) 点击接听≈(%s,%s)",
        max_v,
        left,
        top,
        gx,
        gy,
    )

    old = win32api.GetCursorPos()
    try:
        win32api.SetCursorPos((gx, gy))
        time.sleep(0.06)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, gx, gy, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, gx, gy, 0, 0)
    finally:
        try:
            win32api.SetCursorPos(old)
        except Exception:
            pass

    _last_template_click_at = time.time()
    return {
        "method": "screen_template",
        "x": gx,
        "y": gy,
        "template_left": left,
        "template_top": top,
        "score": float(max_v),
    }
