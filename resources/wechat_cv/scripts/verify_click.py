# -*- coding: utf-8 -*-
"""
每次点击后做正确性验证：截取点击区域前后图，对比或做简单判定，确保点击生效。
"""
import os
import time

try:
    import pyautogui
    import numpy as np
    from PIL import Image
except ImportError as e:
    raise ImportError("需要: pyautogui, numpy, Pillow") from e

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in __import__("sys").path:
    __import__("sys").path.insert(0, _here)
from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front


def capture_region_around(center_x: int, center_y: int, size: int = 80):
    """截取以 (center_x, center_y) 为中心、边长 size 的正方形区域。"""
    half = size // 2
    left = max(0, center_x - half)
    top = max(0, center_y - half)
    im = pyautogui.screenshot(region=(left, top, size, size))
    return np.array(im), (left, top)


def capture_wechat_region(rect, margin_ratio: float = 0.1):
    """截取微信窗口整体或中心区域（用于前后对比）。"""
    x0, y0, w, h = rect
    m = int(min(w, h) * margin_ratio)
    return pyautogui.screenshot(region=(x0 + m, y0 + m, w - 2 * m, h - 2 * m))


def verify_by_diff(before_img, after_img, threshold: float = 5.0):
    """
    通过前后图差异判断是否发生变化（点击可能带来了新界面/高亮等）。
    before_img, after_img: PIL Image 或 ndarray (H,W,C)
    threshold: 平均像素差大于此认为有变化。
    返回 (changed: bool, mean_diff: float)
    """
    if isinstance(before_img, Image.Image):
        before_img = np.array(before_img)
    if isinstance(after_img, Image.Image):
        after_img = np.array(after_img)
    if before_img.shape != after_img.shape:
        return True, float("inf")  # 形状不同认为有变化
    diff = np.abs(before_img.astype(float) - after_img.astype(float))
    mean_diff = float(np.mean(diff))
    return mean_diff > threshold, mean_diff


def click_and_verify(
    x: int, y: int,
    region_size: int = 80,
    wait_after: float = 0.4,
    diff_threshold: float = 5.0,
    max_retries: int = 2,
):
    """
    在 (x,y) 点击，截取该处前后小区域，用差异判断是否「有反应」。
    返回 (success: bool, message: str)。
    """
    _, (left, top) = capture_region_around(x, y, region_size)
    before = pyautogui.screenshot(region=(left, top, region_size, region_size))
    pyautogui.click(x, y)
    time.sleep(wait_after)
    after = pyautogui.screenshot(region=(left, top, region_size, region_size))
    changed, mean_diff = verify_by_diff(before, after, threshold=diff_threshold)
    if changed:
        return True, f"点击后区域有变化 (mean_diff={mean_diff:.2f})"
    if max_retries <= 0:
        return False, f"点击后区域几乎无变化 (mean_diff={mean_diff:.2f})，可能未点中"
    # 再试一次
    time.sleep(0.2)
    before2 = pyautogui.screenshot(region=(left, top, region_size, region_size))
    pyautogui.click(x, y)
    time.sleep(wait_after)
    after2 = pyautogui.screenshot(region=(left, top, region_size, region_size))
    changed2, mean_diff2 = verify_by_diff(before2, after2, threshold=diff_threshold)
    if changed2:
        return True, f"重试后点击有效 (mean_diff={mean_diff2:.2f})"
    return False, f"重试后仍无变化 (mean_diff={mean_diff2:.2f})"


def verify_wechat_whole_window(wait_after: float = 0.5, diff_threshold: float = 3.0):
    """
    对当前微信窗口做「整窗」前后对比（在最近一次点击之后调用）。
    需要调用方在点击前先截一帧并传入，这里只做「再截一帧并对比」的接口。
    返回 (changed, mean_diff)。
    """
    from wechat_cv_send import _find_wechat_handle, _window_rect
    hwnd = _find_wechat_handle()
    if not hwnd:
        return False, 0.0
    rect = _window_rect(hwnd)
    if not rect:
        return False, 0.0
    time.sleep(wait_after)
    after = capture_wechat_region(rect)
    return np.array(after)  # 供外部与 before 对比


def run_click_test_loop(positions_rel: dict, rect):
    """
    根据相对坐标 positions_rel {name: [rx, ry]} 和当前窗口 rect，
    依次点击每个控件并做 verify，打印结果。
    """
    from record_controls import relative_to_pixel
    for name, (rx, ry) in positions_rel.items():
        px, py = relative_to_pixel(rx, ry, rect)
        ok, msg = click_and_verify(px, py, wait_after=0.5)
        print(f"  {name} ({px},{py}): {'OK' if ok else 'FAIL'} - {msg}")
        time.sleep(0.3)


if __name__ == "__main__":
    # 简单测试：对当前鼠标位置做一次点击验证
    x, y = pyautogui.position()
    print("当前鼠标:", x, y)
    ok, msg = click_and_verify(x, y)
    print(ok, msg)
