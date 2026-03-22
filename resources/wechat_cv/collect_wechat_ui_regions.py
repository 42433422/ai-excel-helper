# -*- coding: utf-8 -*-
"""
微信窗口多类别区域标注，用于训练 YOLO 检测：搜索框、联系人卡片、发送按钮、输入区等。
用法：
  1. 方式一：打开微信主窗口，运行  python collect_wechat_ui_regions.py
  2. 方式二：对本地截图标注  python collect_wechat_ui_regions.py "截图.png"
  3. 按 0~3 选类别，鼠标拖拽框选；s 保存，r 重截/重载，q 退出，u 撤销。
"""
import os
import sys
import time

try:
    import cv2
    import numpy as np
except ImportError:
    print("需要: pip install opencv-python numpy")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "yolo_ui_dataset")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
LABELS_DIR = os.path.join(DATASET_DIR, "labels")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)

# YOLO 类别：与 wechat_ui.pt 多类别一致，推理时可按名称取框
CLASSES = [
    "search_box",    # 0 搜索框
    "contact_card",  # 1 联系人/群聊卡片（搜索结果里的一条）
    "send_button",   # 2 发送按钮
    "input_area",    # 3 输入框区域
]
CLASS_COLORS = [
    (0, 255, 0),    # 绿 搜索框
    (255, 165, 0),  # 橙 卡片
    (0, 0, 255),    # 红 发送
    (255, 0, 255),  # 紫 输入区
]


def load_image_from_file(path):
    """从本地文件加载图片，返回 (BGR, (w, h)) 或 (None, None)。"""
    p = os.path.abspath(path)
    if not os.path.isfile(p):
        return None, None
    img = cv2.imread(p)
    if img is None:
        return None, None
    h, w = img.shape[:2]
    return img, (w, h)


def capture_wechat_full():
    """截取整个微信主窗口。"""
    sys.path.insert(0, SCRIPT_DIR)
    try:
        from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front, _capture_region
    except ImportError as e:
        print("无法导入 wechat_cv_send:", e)
        return None, None
    hwnd = _find_wechat_handle()
    if not hwnd:
        print("未找到微信窗口，请先打开微信主界面")
        return None, None
    rect = _window_rect(hwnd)
    if not rect:
        return None, None
    x0, y0, w, h = rect
    _bring_to_front(hwnd)
    time.sleep(0.5)
    img_pil = _capture_region(rect)
    img = np.array(img_pil)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img, (w, h)


def main():
    print("微信 UI 区域标注（多类别）")
    print("  0=搜索框  1=联系人卡片  2=发送按钮  3=输入区")
    print("  先按数字选类别，再鼠标拖拽框选；s 保存  r 重截/重载  q 退出  u 撤销上一个框")
    from_file = None
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        from_file = os.path.abspath(sys.argv[1])
        img, (img_w, img_h) = load_image_from_file(from_file)
        print("已加载本地图片:", from_file)
    else:
        img, (img_w, img_h) = capture_wechat_full()
    if img is None:
        if from_file:
            print("无法读取图片:", from_file)
        else:
            print("未找到微信窗口或截图失败")
        return
    boxes = []  # list of (class_id, x1, y1, x2, y2)
    current_class = 0
    clone = img.copy()
    drawing = False
    start_pt = None
    temp_box = None

    def draw_all():
        nonlocal clone
        clone = img.copy()
        for cid, x1, y1, x2, y2 in boxes:
            color = CLASS_COLORS[cid]
            cv2.rectangle(clone, (x1, y1), (x2, y2), color, 2)
            cv2.putText(clone, CLASSES[cid], (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        if temp_box is not None:
            x1, y1, x2, y2 = temp_box
            color = CLASS_COLORS[current_class]
            cv2.rectangle(clone, (x1, y1), (x2, y2), color, 2)
            cv2.putText(clone, CLASSES[current_class] + " (当前)", (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        # 当前类别提示
        cv2.putText(clone, f"Class: {current_class} {CLASSES[current_class]}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(clone, f"Class: {current_class} {CLASSES[current_class]}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

    def on_mouse(event, x, y, flags, param):
        nonlocal drawing, start_pt, temp_box
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_pt = (x, y)
            temp_box = [x, y, x, y]
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            temp_box[2], temp_box[3] = x, y
            draw_all()
        elif event == cv2.EVENT_LBUTTONUP and drawing:
            drawing = False
            x1, y1 = min(start_pt[0], x), min(start_pt[1], y)
            x2, y2 = max(start_pt[0], x), max(start_pt[1], y)
            if x2 - x1 >= 5 and y2 - y1 >= 5:
                boxes.append((current_class, x1, y1, x2, y2))
            temp_box = None
            draw_all()

    win_name = "微信UI标注: 0~3选类别 拖拽框选 s保存 r重截 q退出 u撤销"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win_name, on_mouse)
    idx = len([f for f in os.listdir(IMAGES_DIR) if f.endswith(".png")])
    draw_all()
    while True:
        cv2.imshow(win_name, clone)
        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            break
        if key in (ord("0"), ord("1"), ord("2"), ord("3")):
            current_class = key - ord("0")
            print("当前类别:", CLASSES[current_class])
            draw_all()
        if key == ord("u"):
            if boxes:
                boxes.pop()
                draw_all()
                print("已撤销上一个框")
        if key == ord("s"):
            if not boxes:
                print("请至少框选一个区域再保存")
                continue
            name = f"ui_{idx:04d}"
            img_path = os.path.join(IMAGES_DIR, name + ".png")
            cv2.imwrite(img_path, img)
            lines = []
            for cid, x1, y1, x2, y2 in boxes:
                xc = ((x1 + x2) / 2) / img_w
                yc = ((y1 + y2) / 2) / img_h
                ww = (x2 - x1) / img_w
                hh = (y2 - y1) / img_h
                xc = max(0, min(1, xc))
                yc = max(0, min(1, yc))
                ww = max(0.01, min(1, ww))
                hh = max(0.01, min(1, hh))
                lines.append(f"{cid} {xc:.6f} {yc:.6f} {ww:.6f} {hh:.6f}\n")
            label_path = os.path.join(LABELS_DIR, name + ".txt")
            with open(label_path, "w") as f:
                f.writelines(lines)
            print(f"已保存 {name}.png ({len(boxes)} 个框)，共 {idx + 1} 张")
            idx += 1
            boxes = []
            temp_box = None
            # 下一张：若来自文件则清空框继续标同一张或等用户按 r 换图；否则实时截微信
            if from_file is None:
                img_new, (img_w, img_h) = capture_wechat_full()
                if img_new is not None:
                    img = img_new
                    draw_all()
                else:
                    print("重新截图失败")
            else:
                draw_all()
        if key == ord("r"):
            if from_file is not None:
                img_new, (img_w, img_h) = load_image_from_file(from_file)
            else:
                img_new, (img_w, img_h) = capture_wechat_full()
            if img_new is not None:
                img = img_new
                boxes = []
                temp_box = None
                draw_all()
                print("已重新加载" if from_file else "已重新截图")
    cv2.destroyAllWindows()
    print("标注数据在:", DATASET_DIR)
    print("类别:", CLASSES)

if __name__ == "__main__":
    main()
