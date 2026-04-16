# -*- coding: utf-8 -*-
"""
按固定比例直接裁剪微信截图，得到搜索框、卡片、发送按钮、输入区等模板图。
用法：python crop_wechat_regions.py [截图路径]
  不传路径则用同目录下 wechat_screenshot_200204.png，或自动找最新截图。
"""
import os
import sys
import glob

try:
    import cv2
    import numpy as np
except ImportError:
    print("需要: pip install opencv-python numpy")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 相对整窗 (左, 上, 宽, 高)，0~1。按常见微信 PC 布局：左侧栏+会话列表约 35%，右侧聊天区 65%
REGIONS = {
    "search_box":    (0.05, 0.00, 0.30, 0.08),   # 左侧顶部搜索条
    "contact_card":  (0.05, 0.10, 0.30, 0.06),   # 左侧第一条会话卡片
    "send_button":   (0.88, 0.92, 0.10, 0.06),   # 右下角发送按钮
    "input_area":    (0.35, 0.88, 0.52, 0.08),   # 底部输入框区域
}
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
DATASET_DIR = os.path.join(SCRIPT_DIR, "yolo_ui_dataset")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
LABELS_DIR = os.path.join(DATASET_DIR, "labels")


def find_screenshot():
    """优先用传入路径，否则同目录下 wechat_screenshot*.png 或 屏幕截图*.png。"""
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        return os.path.abspath(sys.argv[1])
    for name in ["wechat_screenshot_200204.png", "wechat_screenshot.png"]:
        p = os.path.join(SCRIPT_DIR, name)
        if os.path.isfile(p):
            return p
    for p in glob.glob(os.path.join(SCRIPT_DIR, "*.png")):
        if "wechat" in os.path.basename(p).lower() or "截图" in os.path.basename(p):
            return p
    return None


def crop_region(img, name, rel):
    """rel = (left, top, w, h) 0~1，返回裁剪图。"""
    h, w = img.shape[:2]
    left, top, rw, rh = rel
    x1 = int(left * w)
    y1 = int(top * h)
    x2 = int((left + rw) * w)
    y2 = int((top + rh) * h)
    x1 = max(0, min(x1, w - 2))
    y1 = max(0, min(y1, h - 2))
    x2 = max(x1 + 2, min(x2, w))
    y2 = max(y1 + 2, min(y2, h))
    return img[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)


def main():
    path = find_screenshot()
    if not path:
        print("未找到截图。请: python crop_wechat_regions.py 截图.png")
        return
    img = cv2.imread(path)
    if img is None:
        print("无法读取:", path)
        return
    h, w = img.shape[:2]
    print("图片尺寸:", w, "x", h, "| 来源:", path)

    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(LABELS_DIR, exist_ok=True)

    labels_yolo = []  # (class_id, xc, yc, ww, hh) 归一化
    class_names = list(REGIONS.keys())

    for i, (name, rel) in enumerate(REGIONS.items()):
        crop, (x1, y1, cw, ch) = crop_region(img, name, rel)
        out = os.path.join(TEMPLATES_DIR, name + ".png")
        cv2.imwrite(out, crop)
        print("  已裁剪:", name, "->", out, " 尺寸:", cw, "x", ch)
        # YOLO 格式：中心与宽高归一化
        xc = (x1 + cw / 2) / w
        yc = (y1 + ch / 2) / h
        ww = cw / w
        hh = ch / h
        labels_yolo.append((i, xc, yc, ww, hh))

    # 保存整张图到数据集，并写 YOLO 标签（作为第一张训练样本）
    base = os.path.splitext(os.path.basename(path))[0]
    name = "ui_" + base.replace(" ", "_")[:20]
    img_out = os.path.join(IMAGES_DIR, name + ".png")
    cv2.imwrite(img_out, img)
    txt_out = os.path.join(LABELS_DIR, name + ".txt")
    with open(txt_out, "w") as f:
        for cid, xc, yc, ww, hh in labels_yolo:
            f.write(f"{cid} {xc:.6f} {yc:.6f} {ww:.6f} {hh:.6f}\n")
    print("已写入数据集:", img_out, "+", txt_out)
    print("模板目录:", TEMPLATES_DIR)
    print("类别顺序:", class_names)


if __name__ == "__main__":
    main()
