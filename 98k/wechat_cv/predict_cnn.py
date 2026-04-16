# -*- coding: utf-8 -*-
"""
用训练好的 CNN 预测控件位置，再点击；每次点击后调用 verify_click 做正确性测试。
"""
import os
import json
import numpy as np
from PIL import Image

_here = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(_here, "model_cnn")
MODEL_PATH = os.path.join(MODEL_DIR, "best.pt")

if _here not in __import__("sys").path:
    __import__("sys").path.insert(0, _here)
from wechat_cv_send import _find_wechat_handle, _window_rect, _bring_to_front, _capture_region
from verify_click import click_and_verify


def load_model():
    """加载 best.pt 或 last.pt，返回 (model, control_order, image_size)。"""
    try:
        import torch
    except ImportError:
        return None, [], (224, 224)
    path = MODEL_PATH if os.path.isfile(MODEL_PATH) else os.path.join(MODEL_DIR, "last.pt")
    if not os.path.isfile(path):
        return None, [], (224, 224)
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        ckpt = torch.load(path, map_location="cpu")
    from train_cnn import WeChatCNN
    control_order = ckpt.get("control_order", ["search_box", "input_box", "chat_history", "contacts_list"])
    image_size = tuple(ckpt.get("image_size", [224, 224]))
    model = WeChatCNN(num_controls=len(control_order), out_dim=len(control_order) * 2)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, control_order, image_size


def capture_and_preprocess(rect, image_size=(224, 224)):
    """截取微信窗口并预处理为模型输入 (1, 3, H, W)。"""
    img = _capture_region(rect)
    img = img.resize(image_size, Image.Resampling.LANCZOS)
    arr = np.array(img).astype(np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    return np.expand_dims(arr, axis=0)


def predict_positions(model, image_tensor, control_order, device="cpu"):
    """预测各控件相对坐标 (0~1)。返回 {name: (rx, ry)}。"""
    try:
        import torch
    except ImportError:
        return {}
    if model is None:
        return {}
    if isinstance(image_tensor, np.ndarray):
        image_tensor = torch.from_numpy(image_tensor).float().to(device)
    model.to(device)
    with torch.no_grad():
        out = model(image_tensor)
    out = out.cpu().numpy().squeeze()
    out = np.clip(out, 0.0, 1.0)
    res = {}
    for i, name in enumerate(control_order):
        if 2 * i + 1 < len(out):
            res[name] = (float(out[2 * i]), float(out[2 * i + 1]))
    return res


def click_control_with_verify(
    control_name: str,
    positions_rel: dict,
    rect,
    verify: bool = True,
    region_size: int = 80,
    wait_after: float = 0.4,
):
    """
    根据相对坐标点击指定控件，可选做正确性验证。
    返回 (success, message)。
    """
    from record_controls import relative_to_pixel
    if control_name not in positions_rel:
        return False, f"未找到控件 {control_name}"
    rx, ry = positions_rel[control_name]
    px, py = relative_to_pixel(rx, ry, rect)
    if verify:
        ok, msg = click_and_verify(px, py, region_size=region_size, wait_after=wait_after)
        return ok, msg
    import pyautogui
    pyautogui.click(px, py)
    return True, "已点击（未做验证）"


def run_by_cnn(verify_each_click: bool = True, device: str = "cpu"):
    """
    1) 截取微信窗口 2) CNN 预测各控件位置 3) 依次点击并（可选）验证。
    返回 (positions_pred, list_of_verify_results)。
    """
    model, control_order, image_size = load_model()
    if model is None:
        return {}, [("error", "未找到训练好的模型，请先 record_controls -> dataset_cnn -> train_cnn")]

    hwnd = _find_wechat_handle()
    if not hwnd:
        return {}, [("error", "未找到微信窗口")]
    rect = _window_rect(hwnd)
    if not rect:
        return {}, [("error", "无法获取窗口区域")]
    _bring_to_front(hwnd)
    import time
    time.sleep(0.3)

    x = capture_and_preprocess(rect, image_size)
    positions = predict_positions(model, x, control_order, device=device)
    results = []
    for name in control_order:
        if name not in positions:
            results.append((name, False, "未预测到位置"))
            continue
        ok, msg = click_control_with_verify(name, positions, rect, verify=verify_each_click)
        results.append((name, ok, msg))
        time.sleep(0.25)
    return positions, results


if __name__ == "__main__":
    import sys
    verify = "no-verify" not in sys.argv
    pos, res = run_by_cnn(verify_each_click=verify)
    print("预测位置:", pos)
    for name, ok, msg in res:
        print(f"  {name}: {'OK' if ok else 'FAIL'} - {msg}")
