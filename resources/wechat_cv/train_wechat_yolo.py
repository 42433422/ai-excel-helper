# -*- coding: utf-8 -*-
"""
训练微信搜索框 YOLO 模型，生成 wechat_ui.pt。
前置：先运行 collect_search_box_labels.py 采集至少 10+ 张不同窗口大小下的标注。
依赖：ultralytics, opencv-python, numpy
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(SCRIPT_DIR, "yolo_search_dataset")
YAML_PATH = os.path.join(DATASET_DIR, "wechat_search.yaml")
OUTPUT_MODEL = os.path.join(SCRIPT_DIR, "wechat_ui.pt")


def main():
    if not os.path.isfile(YAML_PATH):
        print("未找到 wechat_search.yaml，请先运行 collect_search_box_labels.py 采集数据")
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
    # 使用 nano 小模型，训练快、够用
    model = YOLO("yolov8n.pt")
    model.train(
        data=YAML_PATH,
        epochs=80,
        imgsz=640,
        batch=4,
        project=SCRIPT_DIR,
        name="wechat_search_train",
        exist_ok=True,
        verbose=True,
    )
    # 把最佳权重拷到 wechat_ui.pt
    best = os.path.join(SCRIPT_DIR, "wechat_search_train", "weights", "best.pt")
    if os.path.isfile(best):
        import shutil
        shutil.copy(best, OUTPUT_MODEL)
        print("已保存模型到:", OUTPUT_MODEL)
    else:
        print("训练完成，请手动将 wechat_search_train/weights/best.pt 复制为 wechat_ui.pt")


if __name__ == "__main__":
    main()
