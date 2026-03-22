# -*- coding: utf-8 -*-
"""
从 record_controls 保存的 control_data 构建 CNN 训练数据集：
每条样本 = (窗口截图, 各控件相对坐标 [x1,y1, x2,y2, ...])。
"""
import os
import json
import numpy as np
from PIL import Image

_here = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_here, "control_data")
RECORDS_JSON = os.path.join(DATA_DIR, "control_positions.json")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")
DATASET_DIR = os.path.join(_here, "dataset_cnn")
TRAIN_LIST = os.path.join(DATASET_DIR, "train_list.json")
CONTROL_ORDER = ["search_box", "input_box", "chat_history", "contacts_list"]


def load_records():
    if not os.path.isfile(RECORDS_JSON):
        return []
    with open(RECORDS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def build_dataset(control_order=None, image_size=(224, 224), train_ratio=0.85):
    """
    构建 (image_path 或 image_array, targets) 列表。
    targets: 长度为 len(control_order)*2 的向量，[x1,y1, x2,y2, ...] 相对坐标 0~1。
    """
    control_order = control_order or CONTROL_ORDER
    recs = load_records()
    samples = []
    for r in recs:
        pos = r.get("positions", {})
        target = []
        for c in control_order:
            if c in pos:
                target.extend(pos[c])
            else:
                target.extend([-1.0, -1.0])  # 未标注的用 -1 占位
        if len(target) != len(control_order) * 2:
            continue
        fname = r.get("screenshot", "")
        img_path = os.path.join(SCREENSHOTS_DIR, fname)
        if not os.path.isfile(img_path):
            continue
        samples.append({"image": fname, "target": target, "rect": r.get("rect")})
    np.random.shuffle(samples)
    n = len(samples)
    n_train = max(1, int(n * train_ratio))
    train_list = samples[:n_train]
    val_list = samples[n_train:]
    os.makedirs(DATASET_DIR, exist_ok=True)
    meta = {
        "control_order": control_order,
        "image_size": list(image_size),
        "num_train": len(train_list),
        "num_val": len(val_list),
    }
    with open(os.path.join(DATASET_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(TRAIN_LIST, "w", encoding="utf-8") as f:
        json.dump(train_list, f, ensure_ascii=False, indent=2)
    with open(os.path.join(DATASET_DIR, "val_list.json"), "w", encoding="utf-8") as f:
        json.dump(val_list, f, ensure_ascii=False, indent=2)
    print(f"数据集: train={len(train_list)}, val={len(val_list)}, 控件顺序={control_order}")
    return train_list, val_list, meta


def load_one_sample(item, image_size=(224, 224)):
    """加载一条样本：返回 (img_tensor, target_array)。"""
    img = Image.open(item["image"]).convert("RGB")
    img = img.resize(image_size, Image.Resampling.LANCZOS)
    arr = np.array(img).astype(np.float32) / 255.0
    # 归一化到 [0,1]，通道在最后一维
    target = np.array(item["target"], dtype=np.float32)
    return arr, target


if __name__ == "__main__":
    build_dataset()
