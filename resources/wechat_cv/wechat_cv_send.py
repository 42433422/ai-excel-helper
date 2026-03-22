# -*- coding: utf-8 -*-
"""
纯 CV 方式理解微信界面并发送消息：
- 用 win32 找到微信窗口并截屏
- 用 OCR 识别「搜索」「发送」等文字位置
- 用 pyautogui 在屏幕坐标上点击、粘贴，不依赖 UI 控件树
"""
import time
import os
import sys

try:
    import win32gui
    import win32con
    import win32api
    import pyautogui
    from PIL import Image
    import io
except ImportError as e:
    raise ImportError("需要: pywin32, pyautogui, Pillow。可选: easyocr。") from e

# 可选：easyocr 用于中文 OCR，未安装则用简单启发式（按窗口区域点击）
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

# 可选：OpenCV、numpy（YOLO/模板匹配需要）
try:
    import numpy as np
except ImportError:
    np = None
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

# 微信主窗口类名（含 Qt 版）
WECHAT_MAIN_CLASSES = ("WeChatMainWndForPC", "Qt51514QWindowIcon", "Qt5152QWindowIcon", "Qt64QWindowIcon")
WECHAT_TITLES = ("微信", "Weixin")


def _find_wechat_handle():
    """找到微信主窗口句柄（优先有标题或面积最大的）。"""
    found = []

    def _collect(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            cls = win32gui.GetClassName(hwnd)
            if cls not in WECHAT_MAIN_CLASSES:
                return True
            r = win32gui.GetWindowRect(hwnd)
            w, h = r[2] - r[0], r[3] - r[1]
            if w < 300 or h < 300:
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            found.append((hwnd, title, w * h))
        except Exception:
            pass
        return True

    for c in WECHAT_MAIN_CLASSES:
        win32gui.EnumWindows(_collect, None)
        if found:
            break
    if not found:
        for t in WECHAT_TITLES:
            h = win32gui.FindWindow(None, t)
            if h:
                found.append((h, t, 1))
                break
    if not found:
        return None
    found.sort(key=lambda x: (1 if (x[1] in WECHAT_TITLES or "Weixin" in x[1] or "微信" in x[1]) else 0, x[2]), reverse=True)
    return found[0][0]


def _window_rect(hwnd):
    """窗口客户区或窗口矩形，屏幕坐标。"""
    try:
        r = win32gui.GetWindowRect(hwnd)
        return (r[0], r[1], r[2] - r[0], r[3] - r[1])
    except Exception:
        return None


def _bring_to_front(hwnd):
    """
    激活微信窗口：
    1) 首选 Win+1（你已将微信固定在任务栏第 1 个）；
    2) 若仍无焦点，则还原窗口并在窗口内部点击安全区域；
    3) 全部失败时，最后用一次 SetForegroundWindow 兜底。
    """
    try:
        # 1) 首选：Win+1 激活任务栏第 1 个固定应用（你已设置为微信）
        try:
            pyautogui.hotkey("win", "1")
            time.sleep(0.6)
        except Exception:
            pass

        # 2) 若最小化，则先还原
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)

        # 3) 在窗口内点击一个安全区域把焦点切到微信
        rect = _window_rect(hwnd)
        if not rect:
            # 若仍无法获取窗口矩形，最后退回到系统 API 强制前置一次
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except Exception:
                pass
            return
        try:
            x0, y0, w, h = rect
            click_x = x0 + max(40, int(w * 0.08))
            click_y = y0 + max(40, int(h * 0.12))
            pyautogui.click(click_x, click_y)
            time.sleep(0.25)
        except Exception:
            # 再次失败时，兜底用一次 SetForegroundWindow
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
            except Exception:
                pass
    except Exception:
        # 激活失败时静默忽略，由后续逻辑再次尝试
        pass


def _capture_region(rect):
    """截取屏幕区域 (left, top, width, height)，返回 PIL Image。"""
    x, y, w, h = rect
    # pyautogui 使用 (left, top, width, height)
    im = pyautogui.screenshot(region=(x, y, w, h))
    return im


# 聊天窗口左上角「标题栏」相对区域：用于 OCR 二次确认当前联系人
# (rel_left, rel_top, rel_width, rel_height)，0~1
TITLE_BAR_REGION = (0.0, 0.0, 0.7, 0.12)
# 仅「对话框」区域：排除左侧联系人列表，只取右侧聊天内容区
# 左侧约 28% 为会话列表，从 28% 到 100%，高 12%~90%
CHAT_BODY_REGION = (0.28, 0.12, 0.72, 0.78)
# 搜索框大致在窗口顶部区域，仅在此区域 OCR 可提高识别率
SEARCH_BAR_TOP_RATIO = 0.22  # 搜索框在窗口顶部 22% 高度内
# YOLO 模型路径：环境变量 WECHAT_YOLO_MODEL 或本目录下 wechat_ui.pt（需自训练，类别 0=search_box）
_WECHAT_YOLO_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATES_DIR = os.path.join(_WECHAT_YOLO_DIR, "templates")
WECHAT_YOLO_MODEL_PATH = os.environ.get("WECHAT_YOLO_MODEL") or os.path.join(_WECHAT_YOLO_DIR, "wechat_ui.pt")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(_WECHAT_YOLO_DIR))  # .../FHD

# 模板图（templates 目录下）：搜索框、输入框、列表、对话框、搜索卡片、整个窗口
def _first_existing_template(*names):
    for name in names:
        p = os.path.join(_TEMPLATES_DIR, name)
        if os.path.isfile(p):
            return p
    return None
SEARCH_TEMPLATE_PATH = _first_existing_template("搜索框.png", "search_box.png") or os.path.join(_WECHAT_YOLO_DIR, "search_template.png")
INPUT_BOX_TEMPLATE_PATH = _first_existing_template("输入框.png", "input_area.png")
LIST_TEMPLATE_PATH = _first_existing_template("列表.png")
DIALOG_BUBBLE_TEMPLATE_PATH = _first_existing_template("对话框.png")
SEARCH_CARD_TEMPLATE_PATH = _first_existing_template("搜索卡片.png")
FULL_WINDOW_TEMPLATE_PATH = _first_existing_template("整个.png")


def _crop_relative(img_pil, rel_left, rel_top, rel_width, rel_height):
    """从整窗截图中按相对比例裁出子图。rel 为 0~1。"""
    w, h = img_pil.width, img_pil.height
    crop = img_pil.crop((
        int(rel_left * w),
        int(rel_top * h),
        int((rel_left + rel_width) * w),
        int((rel_top + rel_height) * h),
    ))
    return crop


def _mask_dialog_bubbles_only(img_pil):
    """
    按颜色只保留「对话框气泡」区域：绿色（自己发的）和浅灰/白（对方发的），其余置白。
    这样 OCR 只识别气泡上的字，不会读到联系人列表等。
    """
    import numpy as np
    arr = np.array(img_pil)
    if arr.ndim == 2:
        return img_pil
    r, g, b = arr[:, :, 0].astype(np.int32), arr[:, :, 1].astype(np.int32), arr[:, :, 2].astype(np.int32)
    is_green = (g > 140) & (g > r + 20) & (g > b + 20) & (r < 220) & (b < 220)
    is_light = (r > 200) & (g > 200) & (b > 200) & (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
    is_dark_gray = (r < 80) & (g < 80) & (b < 80) & (r > 30) & (g > 30) & (b > 30)
    mask = is_green | is_light | is_dark_gray
    out = arr.copy()
    out[~mask] = 255
    return Image.fromarray(out.astype(np.uint8))


def _mask_other_bubbles_only(img_pil):
    """
    气泡二次分割：把绿色（自己发的）裁掉，只保留对方气泡。
    绿色更好区分，非绿区域即对方消息，OCR 只跑在对方气泡上。
    """
    import numpy as np
    arr = np.array(img_pil)
    if arr.ndim == 2:
        return img_pil
    r, g, b = arr[:, :, 0].astype(np.int32), arr[:, :, 1].astype(np.int32), arr[:, :, 2].astype(np.int32)
    # 绿色气泡（自己发的）-> 置白，不参与 OCR
    is_green = (g > 130) & (g > r + 15) & (g > b + 15) & (r < 230) & (b < 230)
    # 只保留对方：浅灰/白、深灰
    is_light = (r > 190) & (g > 190) & (b > 190) & (np.abs(r - g) < 50) & (np.abs(g - b) < 50)
    is_dark_gray = (r < 90) & (g < 90) & (b < 90) & (r > 25) & (g > 25) & (b > 25)
    mask_other = (is_light | is_dark_gray) & (~is_green)
    out = arr.copy()
    out[~mask_other] = 255
    return Image.fromarray(out.astype(np.uint8))


def get_current_chat_contact_name(rect=None, use_ocr=True):
    """
    获取当前聊天窗口左上角显示的联系人名称（二次确认）。
    仅对标题栏区域做 OCR，不读整屏，速度快、准确度高。
    返回: {"success": True, "contact_name": "白龙马^_^李秋林", "source": "ocr_title"}
         或 {"success": False, "message": "..."}
    """
    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"success": False, "message": "未找到微信窗口"}
    if rect is None:
        rect = _window_rect(hwnd)
    if not rect:
        return {"success": False, "message": "无法获取窗口区域"}
    x0, y0, w, h = rect
    _bring_to_front(hwnd)
    time.sleep(0.2)
    full = _capture_region(rect)
    rel_left, rel_top, rel_width, rel_height = TITLE_BAR_REGION
    title_img = _crop_relative(full, rel_left, rel_top, rel_width, rel_height)
    if not use_ocr or not HAS_EASYOCR:
        return {"success": False, "message": "需要 easyocr 才能识别标题栏"}
    try:
        import numpy as np
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        arr = np.array(title_img)
        results = reader.readtext(arr)
        if not results:
            return {"success": False, "message": "标题栏未识别到文字"}
        # 按垂直位置分组为「行」，取最上一行作为联系人名（多块拼成一行）
        line_y_threshold = title_img.height * 0.4
        by_line = {}
        for (bbox, text, conf) in results:
            text = (text or "").strip()
            if not text:
                continue
            cy = (bbox[0][1] + bbox[2][1]) / 2
            key = int(cy / line_y_threshold) * line_y_threshold
            by_line.setdefault(key, []).append((cy, text, conf))
        if not by_line:
            return {"success": False, "message": "标题栏未解析到有效文字"}
        first_line_y = min(by_line.keys())
        first_line = sorted(by_line[first_line_y], key=lambda x: x[0])
        contact_name = "".join(t[1] for t in first_line).strip()
        if not contact_name:
            contact_name = (first_line[0][1] if first_line else "").strip()
        return {"success": True, "contact_name": contact_name, "source": "ocr_title"}
    except Exception as e:
        return {"success": False, "message": f"OCR 标题栏失败: {e}"}


def get_current_chat_messages(rect=None, max_lines=80, use_ocr=True):
    """
    气泡二次分割：绿色（自己发的）裁掉，只保留对方气泡再 OCR。
    返回: {"success": True, "messages": [{"role": "other", "text": "..."}, ...], "source": "ocr_chat_body"}
    """
    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"success": False, "message": "未找到微信窗口"}
    if rect is None:
        rect = _window_rect(hwnd)
    if not rect:
        return {"success": False, "message": "无法获取窗口区域"}
    _bring_to_front(hwnd)
    time.sleep(0.2)
    full = _capture_region(rect)
    rel_left, rel_top, rel_width, rel_height = CHAT_BODY_REGION
    body_img = _crop_relative(full, rel_left, rel_top, rel_width, rel_height)
    body_img = _mask_other_bubbles_only(body_img)
    if not use_ocr or not HAS_EASYOCR:
        return {"success": False, "message": "需要 easyocr 才能识别聊天区域"}
    try:
        import numpy as np
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        arr = np.array(body_img)
        results = reader.readtext(arr)
        if not results:
            return {"success": True, "messages": [], "source": "ocr_chat_body"}
        sorted_results = sorted(results, key=lambda r: (r[0][0][1] + r[0][2][1]) / 2)
        line_threshold = body_img.height * 0.04
        lines = []
        current_y, current_parts = None, []
        for (bbox, text, _) in sorted_results:
            text = (text or "").strip()
            if not text:
                continue
            cy = (bbox[0][1] + bbox[2][1]) / 2
            cx = (bbox[0][0] + bbox[2][0]) / 2
            if current_y is None or abs(cy - current_y) <= line_threshold:
                current_y = cy if current_y is None else (current_y + cy) / 2
                current_parts.append((cx, text))
            else:
                if current_parts:
                    current_parts.sort(key=lambda x: x[0])
                    lines.append({"role": "other", "text": " ".join(t[1] for t in current_parts)})
                current_y, current_parts = cy, [(cx, text)]
        if current_parts:
            current_parts.sort(key=lambda x: x[0])
            lines.append({"role": "other", "text": " ".join(t[1] for t in current_parts)})
        return {"success": True, "messages": lines[:max_lines], "source": "ocr_chat_body"}
    except Exception as e:
        return {"success": False, "message": f"OCR 聊天区域失败: {e}"}


def _ocr_find_text(image_pil, texts, reader=None):
    """
    在图像上找文字，返回 (中心x, 中心y, 识别文本) 列表，相对图像坐标。
    texts: 要找的字符串列表，如 ["搜索", "发送"]。
    """
    if not HAS_EASYOCR or reader is None:
        return []
    try:
        import numpy as np
    except ImportError:
        return []
    img = np.array(image_pil)
    results = reader.readtext(img)
    out = []
    for (bbox, text, _) in results:
        text_clean = (text or "").strip()
        for want in texts:
            if want in text_clean or text_clean in want:
                # bbox: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                cx = int((min(xs) + max(xs)) / 2)
                cy = int((min(ys) + max(ys)) / 2)
                out.append((cx, cy, text_clean))
                break
    return out


def _get_yolo_search_model():
    """懒加载 YOLO 模型，用于搜索框检测。模型需自训练，类别 0 或 'search_box' 表示搜索框。"""
    if not HAS_YOLO or not os.path.isfile(WECHAT_YOLO_MODEL_PATH):
        return None
    try:
        return YOLO(WECHAT_YOLO_MODEL_PATH)
    except Exception:
        return None


def _find_search_box_yolo(rect, model):
    """
    用 YOLO 在窗口顶部区域检测搜索框，返回 (screen_x, screen_y) 或 None。
    期望模型类别 0 或名为 search_box 的框。
    """
    if not HAS_YOLO or model is None or np is None:
        return None
    x0, y0, w, h = rect
    crop_h = max(40, min(int(h * SEARCH_BAR_TOP_RATIO), h))
    try:
        img_pil = _capture_region(rect).crop((0, 0, w, crop_h))
        img_np = np.array(img_pil)
        if HAS_CV2:
            if img_np.ndim == 2:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
            elif img_np.shape[2] == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            else:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        results = model.predict(img_np, conf=0.35, verbose=False)
        if not results:
            return None
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return None
        best = None
        best_conf = 0.0
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            names = results[0].names or {}
            name = names.get(cls_id, "")
            if cls_id != 0 and "search" not in name.lower() and "search_box" != name:
                continue
            if conf > best_conf:
                xyxy = boxes.xyxy[i].cpu().numpy()
                cx = int((xyxy[0] + xyxy[2]) / 2)
                cy = int((xyxy[1] + xyxy[3]) / 2)
                best_conf = conf
                best = (x0 + cx, y0 + cy)
        return best
    except Exception:
        return None


def _find_search_box_cv2_template(rect):
    """用 OpenCV 模板匹配在窗口顶部找搜索图标/区域，返回 (screen_x, screen_y) 或 None。"""
    if not HAS_CV2 or np is None or not os.path.isfile(SEARCH_TEMPLATE_PATH):
        return None
    x0, y0, w, h = rect
    crop_h = max(40, min(int(h * SEARCH_BAR_TOP_RATIO), h))
    try:
        img_pil = _capture_region(rect).crop((0, 0, w, crop_h))
        img = np.array(img_pil)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        tpl = cv2.imread(SEARCH_TEMPLATE_PATH)
        if tpl is None:
            return None
        res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < 0.5:
            return None
        th, tw = tpl.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (x0 + cx, y0 + cy)
    except Exception:
        return None


def _find_search_box_position(rect, reader=None, yolo_model=None):
    """
    定位微信主窗口内搜索框中心位置（屏幕坐标）。
    优先级：YOLO > OCR > cv2 模板匹配 > 相对位置 fallback。
    返回 (screen_x, screen_y)。
    """
    x0, y0, w, h = rect
    # 1) YOLO 检测（若已配置 wechat_ui.pt 或 WECHAT_YOLO_MODEL）
    if yolo_model is not None:
        pos = _find_search_box_yolo(rect, yolo_model)
        if pos is not None:
            return pos
    # 2) OpenCV 模板匹配（若存在 search_template.png）
    if HAS_CV2:
        pos = _find_search_box_cv2_template(rect)
        if pos is not None:
            return pos
    # 3) OCR：只截取顶部区域
    if HAS_EASYOCR and reader is not None:
        try:
            img_full = _capture_region(rect)
            crop_h = int(h * SEARCH_BAR_TOP_RATIO)
            if crop_h < 40:
                crop_h = min(40, h)
            img_top = img_full.crop((0, 0, w, crop_h))
            found = _ocr_find_text(img_top, ["搜索", "Search", "搜索聊天内容", "搜一搜"], reader)
            if found:
                cx, cy = found[0][0], found[0][1]
                return (x0 + cx, y0 + cy)
        except Exception:
            pass
    # 4) Fallback：按窗口比例
    rel_y = 0.08
    search_y = y0 + max(40, min(int(h * rel_y), 140))
    return (x0 + w // 2, search_y)


def _click_in_window(hwnd, rel_x, rel_y, rect):
    """在窗口内相对坐标 (rel_x, rel_y) 处点击（转为屏幕坐标）。"""
    x0, y0, _, _ = rect
    sx = x0 + rel_x
    sy = y0 + rel_y
    pyautogui.click(sx, sy)
    time.sleep(0.2)


def _load_template_cv2(path):
    """加载模板图为 BGR numpy，支持中文路径（用 PIL 读再转）。"""
    if not path or not os.path.isfile(path):
        return None
    try:
        tpl = cv2.imread(path)
        if tpl is not None:
            return tpl
    except Exception:
        pass
    try:
        from PIL import Image
        pil_img = Image.open(path)
        if pil_img.mode == "RGBA":
            pil_img = pil_img.convert("RGB")
        tpl = np.array(pil_img)
        if tpl.ndim == 2:
            tpl = cv2.cvtColor(tpl, cv2.COLOR_GRAY2BGR)
        else:
            tpl = cv2.cvtColor(tpl, cv2.COLOR_RGB2BGR)
        return tpl
    except Exception:
        return None


def _find_input_box_by_template(rect):
    """用 templates/输入框.png 在窗口下半部分匹配输入框，返回 (screen_x, screen_y) 或 None。"""
    if not HAS_CV2 or np is None or not INPUT_BOX_TEMPLATE_PATH:
        return None
    x0, y0, w, h = rect
    # 输入框在底部约 45% 高度内（扩大搜索范围）
    crop_top = int(h * 0.55)
    crop_h = h - crop_top
    if crop_h < 50:
        return None
    try:
        img_pil = _capture_region(rect).crop((0, crop_top, w, h))
        img = np.array(img_pil)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        tpl = _load_template_cv2(INPUT_BOX_TEMPLATE_PATH)
        if tpl is None:
            return None
        # 模板过大时缩小再匹配，提高鲁棒性
        th, tw = tpl.shape[:2]
        if tw > w * 0.8 or th > crop_h * 0.8:
            scale = min((w * 0.5) / tw, (crop_h * 0.5) / th)
            if scale < 1:
                new_w, new_h = int(tw * scale), int(th * scale)
                tpl = cv2.resize(tpl, (new_w, new_h))
        res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < 0.32:
            return None
        th, tw = tpl.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (x0 + cx, y0 + crop_top + cy)
    except Exception:
        return None


def send_to_current_chat_by_cv(message: str, delay: float = 1.2, use_ocr: bool = True):
    """
    纯 CV：认为当前前台已是目标聊天。用剪贴板写入内容 -> 点击输入框 -> Ctrl+V 粘贴 -> Enter 发送。
    """
    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"status": "error", "message": "未找到微信窗口，请先打开微信并保持在前台"}
    rect = _window_rect(hwnd)
    if not rect:
        return {"status": "error", "message": "无法获取窗口区域"}
    x0, y0, w, h = rect
    _bring_to_front(hwnd)
    time.sleep(0.5)

    # 1) 输入框位置：优先模板 输入框.png，否则用启发式（输入区在底部，取距底约 12% 的居中点）
    input_pos = _find_input_box_by_template(rect)
    if input_pos is not None:
        input_center_x, input_center_y = input_pos
    else:
        input_center_x = x0 + w // 2
        # 输入框中心约在窗口底部 12% 高度处（发送按钮约在 5% 处）
        input_center_y = y0 + h - max(50, int(h * 0.12))

    # 2) 先写入剪贴板，再点击输入框，再粘贴，保证用剪贴板发送
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            old = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        except Exception:
            old = None
        win32clipboard.CloseClipboard()
    except Exception:
        old = None
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(message, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        return {"status": "error", "message": "无法设置剪贴板"}
    time.sleep(0.15)

    # 3) 点击输入框获得焦点 -> Ctrl+V 粘贴
    pyautogui.click(input_center_x, input_center_y)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(max(0.6, delay))

    # 4) 发送：Enter（微信 PC 默认回车发送）
    pyautogui.press("enter")
    time.sleep(0.3)

    try:
        if old is not None:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(old, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return {"status": "success", "message": "已通过剪贴板粘贴并回车发送到当前聊天"}


def _set_clipboard_image(image_path):
    """将图片文件写入系统剪贴板（CF_DIB），供微信 Ctrl+V 粘贴。返回 True/False。"""
    if not image_path or not os.path.isfile(image_path):
        return False
    try:
        from PIL import Image
        import io
        import win32clipboard
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, "BMP")
        data = out.getvalue()[14:]
        out.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False


def _set_clipboard_files(file_paths):
    """
    将文件列表写入系统剪贴板（CF_HDROP），供微信 Ctrl+V 粘贴文件。返回 True/False。
    """
    if not file_paths:
        return False
    abs_paths = []
    for p in file_paths:
        if not p:
            continue
        ap = os.path.abspath(p)
        if os.path.isfile(ap):
            abs_paths.append(ap)
    if not abs_paths:
        return False
    try:
        import win32clipboard
        import struct

        # DROPFILES 结构（Unicode）：DWORD pFiles; POINT pt; BOOL fNC; BOOL fWide;
        # 参考: https://learn.microsoft.com/en-us/windows/win32/shell/clipboard
        p_files_offset = 20  # 结构体大小
        dropfiles = struct.pack("IiiII", p_files_offset, 0, 0, 0, 1)
        files_str = "\0".join(abs_paths) + "\0\0"
        files_bytes = files_str.encode("utf-16le")
        data = dropfiles + files_bytes

        CF_HDROP = 15
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(CF_HDROP, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False


def send_image_to_current_chat_by_cv(image_path: str, use_ocr: bool = True):
    """将本地图片通过剪贴板粘贴并发送到当前聊天。当前前台需已是目标聊天。"""
    if not _set_clipboard_image(image_path):
        return {"status": "error", "message": "无法读取图片或写入剪贴板"}
    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"status": "error", "message": "未找到微信窗口"}
    rect = _window_rect(hwnd)
    if not rect:
        return {"status": "error", "message": "无法获取窗口区域"}
    _bring_to_front(hwnd)
    time.sleep(0.5)
    input_pos = _find_input_box_by_template(rect)
    if input_pos is not None:
        input_center_x, input_center_y = input_pos
    else:
        x0, y0, w, h = rect
        input_center_x = x0 + w // 2
        input_center_y = y0 + h - max(50, int(h * 0.12))
    pyautogui.click(input_center_x, input_center_y)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.0)
    pyautogui.press("enter")
    time.sleep(0.3)
    return {"status": "success", "message": "已发送图片"}


def send_file_to_current_chat_by_cv(file_path: str, use_ocr: bool = True):
    """
    将本地文件通过剪贴板粘贴并发送到当前聊天。当前前台需已是目标聊天。
    适用于发货单、标签等文件。
    """
    if not (file_path and os.path.isfile(file_path)):
        return {"status": "error", "message": "文件不存在或路径为空"}
    if not _set_clipboard_files([file_path]):
        return {"status": "error", "message": "无法将文件写入剪贴板"}

    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"status": "error", "message": "未找到微信窗口"}
    rect = _window_rect(hwnd)
    if not rect:
        return {"status": "error", "message": "无法获取窗口区域"}
    _bring_to_front(hwnd)
    time.sleep(0.5)

    input_pos = _find_input_box_by_template(rect)
    if input_pos is not None:
        input_center_x, input_center_y = input_pos
    else:
        x0, y0, w, h = rect
        input_center_x = x0 + w // 2
        input_center_y = y0 + h - max(50, int(h * 0.12))
    pyautogui.click(input_center_x, input_center_y)
    time.sleep(0.35)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.0)
    pyautogui.press("enter")
    time.sleep(0.3)
    return {"status": "success", "message": f"已发送文件：{os.path.basename(file_path)}"}


def open_chat_by_cv(contact_name: str, use_ocr: bool = True):
    """
    纯 CV：通过「搜索」找到联系人并打开与该联系人的对话框（不发送消息）。
    - 先将联系人名写入剪贴板 -> 置顶微信 -> 点击搜索框 -> 粘贴联系人名 -> 回车进入第一个搜索结果
    返回: {"status": "success"|"error", "message": "..."}
    """
    if not (contact_name and contact_name.strip()):
        return {"status": "error", "message": "联系人名不能为空"}
    contact_name = contact_name.strip()

    # 先复制联系人名到剪贴板，确保搜索时一定用该名字
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(contact_name, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        return {"status": "error", "message": "无法将联系人名写入剪贴板，请检查 pywin32"}

    hwnd = _find_wechat_handle()
    if not hwnd:
        return {"status": "error", "message": "未找到微信窗口，请先打开微信"}
    rect = _window_rect(hwnd)
    if not rect:
        return {"status": "error", "message": "无法获取窗口区域"}
    # 只在进入搜索流程前激活一次微信窗口，并适当等待，让窗口完全稳定后再找搜索框
    _bring_to_front(hwnd)
    time.sleep(0.8)

    reader = None
    if use_ocr and HAS_EASYOCR:
        try:
            reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
        except Exception:
            pass
    yolo_model = _get_yolo_search_model()
    pos = _find_search_box_position(rect, reader=reader, yolo_model=yolo_model)
    if not pos:
        return {"status": "error", "message": "未能定位到搜索框"}
    search_center_x, search_center_y = pos

    pyautogui.click(search_center_x, search_center_y)
    time.sleep(0.4)
    # 再次写入剪贴板，防止点击后焦点变化导致剪贴板被其它程序改写
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(contact_name, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        pass
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.0)
    pyautogui.press("enter")
    time.sleep(0.8)
    return {"status": "success", "message": f"已打开与「{contact_name}」的对话框"}


def search_and_send_by_cv(friend_name: str, message: str, delay: float = 1.2, use_ocr: bool = True):
    """
    纯 CV：先通过「搜索」找到好友并打开对话框，再发送消息。
    如果已在正确的对话框中，则直接发送。
    - 截屏 -> OCR 找「搜索」-> 点击 -> 粘贴好友名 -> 回车 -> 再发消息
    """
    # 先检查当前是否已在正确的对话框中
    try:
        current = get_current_chat_contact_name(use_ocr=use_ocr)
        if current.get("success") and current.get("contact_name"):
            current_name = current.get("contact_name", "")
            # 如果当前聊天名称包含目标联系人名（模糊匹配），认为已在正确对话框
            if friend_name in current_name or current_name in friend_name:
                time.sleep(0.3)
                return send_to_current_chat_by_cv(message, delay=delay, use_ocr=use_ocr)
    except Exception:
        pass

    # 不在正确对话框中，先打开对话框
    out = open_chat_by_cv(friend_name, use_ocr=use_ocr)
    if out.get("status") != "success":
        return out
    time.sleep(0.5)
    return send_to_current_chat_by_cv(message, delay=delay, use_ocr=use_ocr)


if __name__ == "__main__":
    import json
    if len(sys.argv) > 1 and sys.argv[1] == "get_contact":
        print(json.dumps(get_current_chat_contact_name(use_ocr=HAS_EASYOCR), ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "get_messages":
        max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 80
        print(json.dumps(get_current_chat_messages(max_lines=max_lines, use_ocr=HAS_EASYOCR), ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "open":
        # 用法: python wechat_cv_send.py open "联系人备注或昵称"
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(open_chat_by_cv(name, use_ocr=HAS_EASYOCR), ensure_ascii=False))
    else:
        msg = sys.argv[1] if len(sys.argv) > 1 else "CV测试"
        print(send_to_current_chat_by_cv(msg, delay=1.2, use_ocr=HAS_EASYOCR))
