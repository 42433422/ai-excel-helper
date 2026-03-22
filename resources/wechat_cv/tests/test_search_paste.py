# -*- coding: utf-8 -*-
"""
用剪贴板在搜索框测试：写入指定文本到剪贴板 → 置顶微信 → 点击搜索框 → 粘贴
→ 等待搜索结果 → 点击第一个联系人卡片 → 恢复剪贴板。
若已记录 search_result_first 则用其位置，否则用默认启发式位置（搜索下方第一项）。
用法: python test_search_paste.py [搜索内容]
默认: 白龙马^_^李秋林
"""
import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import pyautogui
from PIL import Image
try:
    import win32api
    import win32con
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front, _capture_region


def _left_click_at(x: int, y: int):
    """在屏幕坐标 (x,y) 发送左键点击，优先 SendInput 再 mouse_event 再 pyautogui。"""
    pyautogui.moveTo(x, y, duration=0.1)
    time.sleep(0.05)
    # 1) 尝试 ctypes SendInput（对部分窗口更可靠）
    try:
        import ctypes
        from ctypes import wintypes
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        INPUT_MOUSE = 0

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

        n = ctypes.wintypes.UINT(1)
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi.dx = 0
        inp.mi.dy = 0
        inp.mi.mouseData = 0
        inp.mi.time = 0
        inp.mi.dwExtraInfo = None
        if ctypes.windll.user32.SetCursorPos(x, y):
            inp.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
            ctypes.windll.user32.SendInput(n, ctypes.byref(inp), ctypes.sizeof(INPUT))
            time.sleep(0.05)
            inp.mi.dwFlags = MOUSEEVENTF_LEFTUP
            ctypes.windll.user32.SendInput(n, ctypes.byref(inp), ctypes.sizeof(INPUT))
            return
    except Exception:
        pass
    # 2) win32 mouse_event
    if _HAS_WIN32:
        try:
            win32api.SetCursorPos((x, y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            return
        except Exception:
            pass
    # 3) pyautogui
    pyautogui.click(x, y, button="left")
from record_controls import (
    load_records,
    get_merged_positions_latest,
    relative_to_pixel,
    pixel_to_relative,
    SCREENSHOTS_DIR,
    _ensure_dirs,
    save_records,
)

# 未记录「第一个搜索结果」时使用的相对位置（搜索框下方第一行联系人）
SEARCH_RESULT_FIRST_FALLBACK = (0.28, 0.16)
WAIT_AFTER_PASTE = 1.0


def set_clipboard(text: str):
    import win32clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()


def get_clipboard():
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except Exception:
        data = None
    win32clipboard.CloseClipboard()
    return data


def _pick_search_result_first_on_image(img, rect, screenshot_path=None):
    """
    显示联系人卡片截图，用户点击第一个联系人位置。
    返回 (rx, ry, screen_px, screen_py) 或 (None, None, None, None)。
    """
    if img is None and screenshot_path and os.path.isfile(screenshot_path):
        img = Image.open(screenshot_path).convert("RGB")
    if img is None:
        return (None, None, None, None)
    try:
        import tkinter as tk
        from PIL import ImageTk
    except ImportError:
        print("需要 tkinter 才能点选联系人位置")
        return (None, None, None, None)
    x0, y0, w, h = rect
    root = tk.Tk()
    root.title("请点击第一个联系人卡片")
    root.geometry(f"{min(w, 900)}x{min(h, 700)}+100+100")
    img_resized = img.copy()
    img_resized.thumbnail((900, 700), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img_resized)
    lab = tk.Label(root, image=photo)
    lab.pack()
    scale_x = img.width / img_resized.width
    scale_y = img.height / img_resized.height
    tip = tk.StringVar(value="请在图中点击第一个联系人卡片（搜索结果第一项）")
    tk.Label(root, textvariable=tip, font=("", 12)).pack(pady=8)
    result = [None]

    def on_click(event):
        img_x = event.x * scale_x
        img_y = event.y * scale_y
        screen_px = x0 + img_x
        screen_py = y0 + img_y
        rx, ry = pixel_to_relative(screen_px, screen_py, rect)
        result[0] = (round(rx, 4), round(ry, 4), int(screen_px), int(screen_py))
        tip.set(f"已选位置 ({rx:.3f}, {ry:.3f})，关闭窗口继续")
        root.quit()

    lab.bind("<Button-1>", on_click)
    root.mainloop()
    root.destroy()
    if result[0] is None:
        return (None, None, None, None)
    rx, ry, spx, spy = result[0]
    return (rx, ry, spx, spy)


def test_search_box_paste(search_text: str = "白龙马^_^李秋林"):
    data = load_records()
    records = data.get("records", [])
    if not records:
        print("尚未记录控件位置，请先运行: python record_controls.py ocr")
        return

    # 使用合并位置（保证同时有 search_box 与 search_result_first，来自不同帧也可）
    positions = get_merged_positions_latest()
    if "search_box" not in positions:
        print("未找到 search_box 位置，请先标注搜索框")
        return

    hwnd = _find_wechat_handle()
    if not hwnd:
        print("未找到微信窗口，请先打开微信")
        return
    rect = _window_rect(hwnd)
    if not rect:
        print("无法获取窗口区域")
        return

    old_clip = None
    try:
        old_clip = get_clipboard()
    except Exception:
        pass

    set_clipboard(search_text)
    time.sleep(0.15)

    _bring_to_front(hwnd)
    time.sleep(0.4)

    rx, ry = positions["search_box"]
    px, py = relative_to_pixel(rx, ry, rect)
    pyautogui.click(px, py)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(WAIT_AFTER_PASTE)

    # 联系人卡片已出现：截图保存
    _ensure_dirs()
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "._^" else "_" for c in search_text)[:30]
    screenshot_name = f"search_result_{safe_name}_{ts}.png"
    screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)
    x0, y0, w, h = rect
    try:
        img = _capture_region(rect)
        img.save(screenshot_path)
        print(f"已保存联系人卡片截图: {screenshot_path}")
    except Exception as e:
        print(f"截图保存失败: {e}")
        img = None

    # 第一个联系人卡片：置顶微信 → 移到卡片位置 → 移动后停留 1.5 秒 → 左键点击
    _bring_to_front(hwnd)
    time.sleep(0.4)

    if "search_result_first" in positions:
        rx, ry = positions["search_result_first"]
        card_x, card_y = relative_to_pixel(rx, ry, rect)
    else:
        rx, ry, card_x, card_y = _pick_search_result_first_on_image(img, rect, screenshot_path)
        if rx is None:
            print("未在截图上点选，跳过点击联系人卡片")
            card_x = card_y = None
        else:
            _bring_to_front(hwnd)
            time.sleep(0.4)
            # 保存到 records 供下次使用
            data = load_records()
            last_positions = dict(data["records"][-1].get("positions", {})) if data.get("records") else {}
            last_positions["search_result_first"] = [rx, ry]
            frame = {"rect": list(rect), "positions": last_positions, "timestamp": ts, "source": "search_result_pick"}
            frame["screenshot"] = screenshot_name
            data["records"].append(frame)
            save_records(data)
            print(f"已保存 search_result_first: ({rx:.3f}, {ry:.3f})，下次将自动点击该位置")

    if card_x is not None and card_y is not None:
        pyautogui.moveTo(card_x, card_y, duration=0.2)
        time.sleep(1.5)  # 移动后停留，再点击
        for _ in range(3):  # 多试几次点击，提高命中
            _left_click_at(card_x, card_y)
            time.sleep(0.25)
        time.sleep(0.3)

    if old_clip is not None:
        try:
            set_clipboard(old_clip)
        except Exception:
            pass

    print(f"已点击搜索框、粘贴并点击联系人卡片: {search_text}")


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "白龙马^_^李秋林"
    test_search_box_paste(text)
