# -*- coding: utf-8 -*-
"""
训练微信 UI 多类别 YOLO 模型（搜索框、卡片、发送按钮、输入区），生成 wechat_ui.pt。
前置：先运行 collect_wechat_ui_regions.py 采集标注。
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "yolo_ui_dataset")
YAML_PATH = os.path.join(DATASET_DIR, "wechat_ui.yaml")
OUTPUT_MODEL = os.path.join(SCRIPT_DIR, "wechat_ui.pt")


def main():
    if not os.path.isfile(YAML_PATH):
        print("未找到 wechat_ui.yaml，请先运行 collect_wechat_ui_regions.py 采集数据")
        sys.exit(1)
    imgs = os.path.join(DATASET_DIR, "images")
    if not os.path.isdir(imgs) or len([f for f in os.listdir(imgs) if f.endswith(".png")]) < 5:
        print("请至少采集 5 张以上标注图再训练（建议 10+ 张）")
        sys.exit(1)
    try:
        from ultralytics import YOLO
    except ImportError:
        print("请安装: pip install ultralytics")
        sys.exit(1)
    model = YOLO("yolov8n.pt")
    model.train(
        data=YAML_PATH,
        epochs=100,
        imgsz=640,
        batch=4,
        project=SCRIPT_DIR,
        name="wechat_ui_train",
        exist_ok=True,
        verbose=True,
    )
    best = os.path.join(SCRIPT_DIR, "wechat_ui_train", "weights", "best.pt")
    if os.path.isfile(best):
        import shutil
        shutil.copy(best, OUTPUT_MODEL)
        print("已保存模型到:", OUTPUT_MODEL)
    else:
        print("请手动将 wechat_ui_train/weights/best.pt 复制为 wechat_ui.pt")


if __name__ == "__main__":
    main()
