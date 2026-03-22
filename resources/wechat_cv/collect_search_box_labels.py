# -*- coding: utf-8 -*-
"""
采集「搜索框」标注数据，用于训练 YOLO 模型 wechat_ui.pt。
用法：
  1. 先打开微信主窗口。
  2. 运行: python collect_search_box_labels.py
  3. 在弹窗里用鼠标拖拽框出搜索框区域，按 s 保存、q 退出。
  4. 多换几种窗口大小/DPI 采集 10+ 张后，运行 train_wechat_yolo.py 训练。
"""
import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("需要: pip install opencv-python numpy")
    sys.exit(1)

# 与 wechat_cv_send 一致的顶部裁剪比例
SEARCH_BAR_TOP_RATIO = 0.22
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "yolo_search_dataset")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
LABELS_DIR = os.path.join(DATASET_DIR, "labels")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)


def capture_wechat_top_region():
    """截取微信窗口顶部区域（与推理时一致）。"""
    sys.path.insert(0, SCRIPT_DIR)
    try:
        from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front, _capture_region, SEARCH_BAR_TOP_RATIO
    except ImportError as e:
        print("无法导入 wechat_cv_send:", e)
        return None, None, None
    hwnd = _find_wechat_handle()
    if not hwnd:
        print("未找到微信窗口，请先打开微信主界面")
        return None, None, None
    rect = _window_rect(hwnd)
    if not rect:
        return None, None, None
    x0, y0, w, h = rect
    _bring_to_front(hwnd)
    import time
    time.sleep(0.5)
    crop_h = max(40, min(int(h * SEARCH_BAR_TOP_RATIO), h))
    img_pil = _capture_region(rect).crop((0, 0, w, crop_h))
    img = np.array(img_pil)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img, (x0, y0, w, crop_h), (w, crop_h)


def main():
    print("请确保微信主窗口已打开。按 s 保存当前框选，q 退出，r 重新截一张。")
    img, rect, (crop_w, crop_h) = capture_wechat_top_region()
    if img is None:
        return
    x0, y0, w, h = rect
    clone = img.copy()
    box = [0, 0, 0, 0]  # x1,y1,x2,y2
    drawing = False
    start_pt = None

    def on_mouse(event, x, y, flags, param):
        nonlocal drawing, start_pt, clone, box
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_pt = (x, y)
            box = [x, y, x, y]
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            box[2], box[3] = x, y
            clone = img.copy()
            cv2.rectangle(clone, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            box[2], box[3] = x, y
            if box[0] > box[2]:
                box[0], box[2] = box[2], box[0]
            if box[1] > box[3]:
                box[1], box[3] = box[3], box[1]
            clone = img.copy()
            cv2.rectangle(clone, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)

    cv2.namedWindow("框选搜索框后按 s 保存", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("框选搜索框后按 s 保存", on_mouse)
    idx = len([f for f in os.listdir(IMAGES_DIR) if f.endswith(".png")])
    while True:
        cv2.imshow("框选搜索框后按 s 保存", clone)
        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            break
        if key == ord("s"):
            x1, y1, x2, y2 = box
            if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                print("框太小，请重新拖拽框选搜索框")
                continue
            name = f"search_{idx:04d}"
            img_path = os.path.join(IMAGES_DIR, name + ".png")
            cv2.imwrite(img_path, img)
            # YOLO 格式：class_id x_center y_center width height（归一化 0~1）
            xc = ((x1 + x2) / 2) / crop_w
            yc = ((y1 + y2) / 2) / crop_h
            ww = (x2 - x1) / crop_w
            hh = (y2 - y1) / crop_h
            xc = max(0, min(1, xc))
            yc = max(0, min(1, yc))
            ww = max(0.01, min(1, ww))
            hh = max(0.01, min(1, hh))
            label_path = os.path.join(LABELS_DIR, name + ".txt")
            with open(label_path, "w") as f:
                f.write(f"0 {xc:.6f} {yc:.6f} {ww:.6f} {hh:.6f}\n")
            print(f"已保存 {name}.png + .txt，共 {idx + 1} 张")
            idx += 1
            # 下一张：重新截图
            out = capture_wechat_top_region()
            if out[0] is None:
                break
            img, rect, (crop_w, crop_h) = out
            clone = img.copy()
            box = [0, 0, 0, 0]
        if key == ord("r"):
            img, rect, (crop_w, crop_h) = capture_wechat_top_region()
            if img is not None:
                clone = img.copy()
                box = [0, 0, 0, 0]
            else:
                print("重新截图失败")
    cv2.destroyAllWindows()
    print("标注数据在:", DATASET_DIR)


if __name__ == "__main__":
    main()
