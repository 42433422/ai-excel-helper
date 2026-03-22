# -*- coding: utf-8 -*-
"""
记录微信窗口内所有控件的位置，用于后续 CNN 训练与点击。
- 截取微信窗口，在图上点击标注控件名称，保存为「相对坐标」(0~1) 和可选截图。
- 支持多帧（不同窗口大小/状态）累积到同一数据集。
"""
import os
import json
import time

try:
    import win32gui
    import win32con
    import pyautogui
    from PIL import Image
    import numpy as np
except ImportError as e:
    raise ImportError("需要: pywin32, pyautogui, Pillow, numpy") from e

# 复用 wechat_cv_send 的找窗
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in __import__("sys").path:
    __import__("sys").path.insert(0, _here)
from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front, _capture_region

# 默认控件：搜索框、对话框、聊天记录、联系人列表
DEFAULT_CONTROLS = [
    "search_box",       # 搜索框（顶部）
    "input_box",        # 对话框（输入消息的区域）
    "chat_history",     # 聊天记录（消息列表区域）
    "contacts_list",    # 联系人列表（左侧会话列表）
]

DATA_DIR = os.path.join(_here, "control_data")
RECORDS_JSON = os.path.join(DATA_DIR, "control_positions.json")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def load_records():
    _ensure_dirs()
    if not os.path.isfile(RECORDS_JSON):
        return {"records": [], "controls": list(DEFAULT_CONTROLS)}
    with open(RECORDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_records(data):
    _ensure_dirs()
    with open(RECORDS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def capture_wechat_image():
    """截取当前微信窗口图，返回 (PIL Image, rect, hwnd)。"""
    hwnd = _find_wechat_handle()
    if not hwnd:
        return None, None, None
    rect = _window_rect(hwnd)
    if not rect:
        return None, None, hwnd
    _bring_to_front(hwnd)
    time.sleep(0.3)
    img = _capture_region(rect)
    return img, rect, hwnd


def pixel_to_relative(px, py, rect):
    """窗口内像素坐标 -> 相对坐标 (0~1)。"""
    x0, y0, w, h = rect
    rx = (px - x0) / w if w else 0
    ry = (py - y0) / h if h else 0
    return (round(rx, 4), round(ry, 4))


def relative_to_pixel(rx, ry, rect):
    """相对坐标 (0~1) -> 窗口内像素（屏幕坐标）。"""
    x0, y0, w, h = rect
    px = x0 + rx * w
    py = y0 + ry * h
    return (int(px), int(py))


def record_one_frame_interactive():
    """
    交互式记录一帧：截屏后用户在控制台按「控件名」再在窗口上点击，将点击位置记为该控件。
    或：显示图片，用键盘选控件后鼠标下次点击即记录（需图形界面）。
    这里做「无 GUI」版本：提示用户用我们提供的简单 Tk 窗口点击标注。
    """
    try:
        import tkinter as tk
        from PIL import ImageTk
    except ImportError:
        print("需要 tkinter。改用「按控件名输入坐标」方式。")
        return _record_one_frame_cli()
    img, rect, hwnd = capture_wechat_image()
    if img is None or rect is None:
        print("未找到微信窗口或无法截屏")
        return None
    x0, y0, w, h = rect
    data = load_records()
    controls = data.get("controls", list(DEFAULT_CONTROLS))
    positions = {}  # control_name -> (rx, ry)
    idx = [0]  # 当前要标的控件下标

    root = tk.Tk()
    root.title("点击标注控件（按顺序）: " + ", ".join(controls))
    root.geometry(f"{min(w, 900)}x{min(h, 700)}+100+100")
    img_resized = img.copy()
    img_resized.thumbnail((900, 700), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img_resized)
    lab = tk.Label(root, image=photo)
    lab.pack()
    scale_x = img.width / img_resized.width
    scale_y = img.height / img_resized.height
    tip = tk.StringVar(value=f"请点击: {controls[0]}")

    def on_click(event):
        if idx[0] >= len(controls):
            tip.set("已标完，关闭窗口保存")
            return
        # 点击在缩放图上的坐标 -> 还原到原图（即窗口）坐标
        px = x0 + event.x * scale_x
        py = y0 + event.y * scale_y
        rx, ry = pixel_to_relative(px, py, rect)
        cname = controls[idx[0]]
        positions[cname] = [rx, ry]
        tip.set(f"已标 {cname} -> ({rx:.3f}, {ry:.3f}). 下一个: " + (controls[idx[0]+1] if idx[0]+1 < len(controls) else "无，关闭保存"))
        idx[0] += 1

    lab.bind("<Button-1>", on_click)
    tk.Label(root, textvariable=tip, font=("", 12)).pack(pady=8)
    tk.Button(root, text="跳过当前控件", command=lambda: (idx.__setitem__(0, idx[0] + 1), tip.set(f"下一个: " + (controls[idx[0]] if idx[0] < len(controls) else "无")))).pack()
    tk.Button(root, text="保存并关闭", command=root.quit).pack(pady=4)

    root.mainloop()
    root.destroy()

    if not positions:
        print("未标注任何控件")
        return None
    # 保存这一帧
    frame = {
        "rect": list(rect),
        "positions": positions,
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
    }
    fname = f"frame_{frame['timestamp']}.png"
    img.save(os.path.join(SCREENSHOTS_DIR, fname))
    frame["screenshot"] = fname
    data["records"].append(frame)
    save_records(data)
    print("已保存:", RECORDS_JSON, "本帧控件:", list(positions.keys()))
    return frame


def _record_one_frame_cli():
    """无 GUI：根据提示输入控件名和坐标（用户可自己看微信窗口用其它工具取坐标）。"""
    img, rect, hwnd = capture_wechat_image()
    if img is None or rect is None:
        print("未找到微信窗口")
        return None
    data = load_records()
    controls = data.get("controls", list(DEFAULT_CONTROLS))
    positions = {}
    x0, y0, w, h = rect
    print(f"窗口 rect: left={x0}, top={y0}, width={w}, height={h}")
    print("输入相对坐标 (0~1 之间，用空格分隔 x y)，或输入 q 结束")
    for c in controls:
        s = input(f"  {c} 的 x y (或 q 跳过): ").strip()
        if s.lower() == "q":
            continue
        try:
            parts = s.split()
            rx, ry = float(parts[0]), float(parts[1])
            positions[c] = [round(rx, 4), round(ry, 4)]
        except Exception:
            print("    格式错误，跳过")
    if not positions:
        return None
    frame = {"rect": list(rect), "positions": positions, "timestamp": time.strftime("%Y%m%d_%H%M%S")}
    fname = f"frame_{frame['timestamp']}.png"
    img.save(os.path.join(SCREENSHOTS_DIR, fname))
    frame["screenshot"] = fname
    data["records"].append(frame)
    save_records(data)
    return frame


# OCR 自动标注：控件名 -> (界面文字关键词, 区域约束)
# 约束: "top"=ry<0.2, "left"=rx<0.35, "bottom"=ry>0.75, "right"=rx>0.6, None=不限制
CONTROL_OCR_TEXTS = {
    "search_box": (["搜索", "Search"], "top"),       # 搜索框在顶部
    "input_box": (["输入", "请输入", "Type", "消息"], "bottom"),  # 对话框在下方
    "chat_history": (["消息", "聊天记录", "Chat"], "mid"),       # 聊天记录在中间主区域
    "contacts_list": (["会话", "联系人", "Chats"], "left"),       # 联系人/会话列表在左侧
}


def _in_region(rx, ry, region):
    if region is None:
        return True
    if region == "top":
        return ry < 0.25
    if region == "bottom":
        return ry > 0.7
    if region == "left":
        return rx < 0.35
    if region == "right":
        return rx > 0.6
    if region == "mid":
        return 0.2 < ry < 0.8 and 0.25 < rx < 0.85
    return True


def _reject_wrong_match(control_name, text_clean, rx, ry):
    """排除错误匹配，例如不要把「发送视频」当成搜索框。"""
    # 严禁把带「视频」的当成普通控件
    if "视频" in text_clean and control_name != "send_video":
        return True
    # 「发送」只接受纯发送按钮：在窗口很下方且偏右（避免 发送视频/发送文件）
    if "发送" in text_clean or "Send" in text_clean:
        if control_name == "search_box":
            return True  # 发送不是搜索
        if control_name == "contacts_list":
            return True
    return False


def auto_label_by_ocr():
    """
    用 OCR 识别：搜索框、对话框、聊天记录、联系人列表。按区域约束取匹配，避免点到发送视频等。
    """
    try:
        import easyocr
        import numpy as np
    except ImportError:
        print("未安装 easyocr，无法自动标注。请: pip install easyocr")
        return None
    img, rect, hwnd = capture_wechat_image()
    if img is None or rect is None:
        print("未找到微信窗口或无法截屏")
        return None
    x0, y0, w, h = rect
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
    arr = np.array(img)
    results = reader.readtext(arr)
    positions = {}
    for control_name, (keywords, region) in CONTROL_OCR_TEXTS.items():
        candidates = []  # (rx, ry, text)
        for (bbox, text, _) in results:
            text_clean = (text or "").strip()
            for kw in keywords:
                if kw not in text_clean and text_clean != kw:
                    continue
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                cx = (min(xs) + max(xs)) / 2
                cy = (min(ys) + max(ys)) / 2
                rx = round(cx / w, 4)
                ry = round(cy / h, 4)
                if _reject_wrong_match(control_name, text_clean, rx, ry):
                    continue
                if 0 <= rx <= 1 and 0 <= ry <= 1 and _in_region(rx, ry, region):
                    candidates.append((rx, ry, text_clean))
                    break
        if candidates:
            # 搜索框取最上的；联系人取最左的；对话框取最下的；聊天记录取中间的
            if region == "top":
                candidates.sort(key=lambda c: c[1])
            elif region == "left":
                candidates.sort(key=lambda c: c[0])
            elif region == "bottom":
                candidates.sort(key=lambda c: -c[1])
            else:
                candidates.sort(key=lambda c: abs(c[0] - 0.5) + abs(c[1] - 0.5))
            positions[control_name] = [candidates[0][0], candidates[0][1]]
    # 启发式兜底
    if "search_box" not in positions:
        positions["search_box"] = [0.5, 0.06]
    if "input_box" not in positions:
        positions["input_box"] = [0.5, round(1 - 0.18, 4)]
    if "chat_history" not in positions:
        positions["chat_history"] = [0.5, 0.5]
    if "contacts_list" not in positions:
        positions["contacts_list"] = [0.08, 0.35]
    _ensure_dirs()
    frame = {
        "rect": list(rect),
        "positions": positions,
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "source": "ocr_auto",
    }
    fname = f"frame_{frame['timestamp']}.png"
    img.save(os.path.join(SCREENSHOTS_DIR, fname))
    frame["screenshot"] = fname
    data = load_records()
    data["records"].append(frame)
    save_records(data)
    print("OCR 自动标注完成，已保存:", list(positions.keys()))
    return frame


def get_merged_positions_latest():
    """从所有记录中合并位置，同一控件取「最新一帧」的值（后面的覆盖前面的）。用于全流程时同时用到 search_box 与 search_result_first。"""
    data = load_records()
    records = data.get("records", [])
    merged = {}
    for r in records:
        merged.update(r.get("positions", {}))
    return merged


def get_average_positions():
    """对所有已记录帧求各控件位置的平均（相对坐标），用于无 CNN 时的默认点击。"""
    data = load_records()
    recs = data.get("records", [])
    if not recs:
        return {}
    controls = data.get("controls", list(DEFAULT_CONTROLS))
    from collections import defaultdict
    sums = defaultdict(lambda: [0.0, 0.0])
    cnt = defaultdict(int)
    for r in recs:
        for c, (rx, ry) in r.get("positions", {}).items():
            sums[c][0] += rx
            sums[c][1] += ry
            cnt[c] += 1
    out = {}
    for c in controls:
        if cnt[c] > 0:
            out[c] = [round(sums[c][0] / cnt[c], 4), round(sums[c][1] / cnt[c], 4)]
    return out


def _set_clipboard(text):
    import win32clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()


def record_search_result_first(search_text: str = "白龙马^_^李秋林", wait_after_paste: float = 1.2):
    """
    全流程：在搜索框粘贴指定关键词 -> 等联系人卡片出现 -> 截屏 -> 用户在图上点击「第一个联系人卡片」-> 保存为 search_result_first。
    会合并到已有记录（沿用上一帧的 search_box 等，只新增/覆盖 search_result_first）。
    """
    try:
        import tkinter as tk
        from PIL import ImageTk
    except ImportError:
        print("需要 tkinter 才能进行点击标注")
        return None
    data = load_records()
    records = data.get("records", [])
    if not records:
        print("请先运行 python record_controls.py ocr 或 python record_controls.py 记录至少一帧（含 search_box）")
        return None
    last_positions = dict(records[-1].get("positions", {}))
    if "search_box" not in last_positions:
        print("上一帧中未找到 search_box，请先标注搜索框")
        return None

    hwnd = _find_wechat_handle()
    if not hwnd:
        print("未找到微信窗口，请先打开微信")
        return None
    rect = _window_rect(hwnd)
    if not rect:
        print("无法获取窗口区域")
        return None
    x0, y0, w, h = rect
    _bring_to_front(hwnd)
    time.sleep(0.4)

    _set_clipboard(search_text)
    time.sleep(0.15)
    px, py = relative_to_pixel(last_positions["search_box"][0], last_positions["search_box"][1], rect)
    pyautogui.click(px, py)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(wait_after_paste)

    img, rect2, _ = capture_wechat_image()
    if img is None or rect2 is None:
        print("粘贴后截屏失败")
        return None
    rect = rect2
    x0, y0, w, h = rect

    root = tk.Tk()
    root.title("请点击「第一个联系人卡片」位置")
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
        px_ = x0 + event.x * scale_x
        py_ = y0 + event.y * scale_y
        rx, ry = pixel_to_relative(px_, py_, rect)
        result[0] = [round(rx, 4), round(ry, 4)]
        tip.set(f"已记录 search_result_first -> ({rx:.3f}, {ry:.3f})，关闭窗口保存")
        root.quit()

    lab.bind("<Button-1>", on_click)
    root.mainloop()
    root.destroy()

    if result[0] is None:
        print("未点击，未保存")
        return None
    last_positions["search_result_first"] = result[0]
    frame = {
        "rect": list(rect),
        "positions": last_positions,
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "source": "search_result_record",
    }
    fname = f"frame_{frame['timestamp']}.png"
    img.save(os.path.join(SCREENSHOTS_DIR, fname))
    frame["screenshot"] = fname
    _ensure_dirs()
    data["records"].append(frame)
    save_records(data)
    print("已保存 search_result_first，本帧控件:", list(last_positions.keys()))
    return frame


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "avg":
        print("平均位置:", get_average_positions())
    elif len(sys.argv) > 1 and sys.argv[1] in ("ocr", "auto"):
        auto_label_by_ocr()
    elif len(sys.argv) > 1 and sys.argv[1] == "search_result":
        search_text = sys.argv[2] if len(sys.argv) > 2 else "白龙马^_^李秋林"
        record_search_result_first(search_text)
    else:
        record_one_frame_interactive()
