# -*- coding: utf-8 -*-
"""
用已记录的控件位置（平均或单帧）依次点击，并对每次点击做正确性验证。
保证先测试每次点击是否正确，再用于自动控制。
"""
import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front
from record_controls import load_records, get_average_positions, relative_to_pixel
from verify_click import click_and_verify


def test_all_clicks(use_average=True, verify=True, only_control=None):
    """
    use_average: True 用所有帧平均位置，False 用最新一帧位置。
    verify: 每次点击后是否做前后截图差异验证。
    only_control: 若指定（如 'search_box'），仅测试该控件。
    """
    data = load_records()
    records = data.get("records", [])
    if not records:
        print("尚未记录任何控件位置，请先运行: python record_controls.py")
        return

    if use_average:
        positions = get_average_positions()
        print("使用平均位置:", positions)
    else:
        positions = records[-1].get("positions", {})
        print("使用最新一帧位置:", positions)

    if only_control:
        if only_control not in positions:
            print(f"未找到控件 '{only_control}'，可选: {list(positions.keys())}")
            return
        positions = {only_control: positions[only_control]}
        print(f"仅测试: {only_control}")

    hwnd = _find_wechat_handle()
    if not hwnd:
        print("未找到微信窗口，请先打开微信并置于前台")
        return
    rect = _window_rect(hwnd)
    if not rect:
        print("无法获取窗口区域")
        return
    _bring_to_front(hwnd)
    time.sleep(0.4)

    results = []
    for name, (rx, ry) in positions.items():
        px, py = relative_to_pixel(rx, ry, rect)
        if verify:
            ok, msg = click_and_verify(px, py, wait_after=0.5)
            results.append((name, (px, py), ok, msg))
            print(f"  {name}  ({px},{py}): {'OK' if ok else 'FAIL'} {msg}")
        else:
            import pyautogui
            pyautogui.click(px, py)
            results.append((name, (px, py), None, "未验证"))
            print(f"  {name}  ({px},{py}): 已点击（未验证）")
        time.sleep(0.35)

    return results


if __name__ == "__main__":
    use_avg = "latest" not in sys.argv
    no_verify = "no-verify" in sys.argv
    only_control = None
    for a in sys.argv[1:]:
        if a not in ("latest", "no-verify") and not a.startswith("-"):
            only_control = a
            break
    test_all_clicks(use_average=use_avg, verify=not no_verify, only_control=only_control)
