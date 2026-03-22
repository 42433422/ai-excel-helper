# -*- coding: utf-8 -*-
"""
CNN 模型：输入微信窗口截图，输出各控件相对坐标 (0~1)。
训练完成后用于快速预测点击位置；推理时再配合 verify_click 做点击正确性测试。
"""
import os
import json
import numpy as np

_here = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(_here, "dataset_cnn")
MODEL_DIR = os.path.join(_here, "model_cnn")
os.makedirs(MODEL_DIR, exist_ok=True)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class WeChatControlDataset(Dataset):
    def __init__(self, list_path, image_size=(224, 224), control_order=None):
        with open(list_path, "r", encoding="utf-8") as f:
            self.samples = json.load(f)
        self.image_size = image_size
        self.control_order = control_order or ["search", "chats_btn", "contacts_btn", "input_center", "send_btn"]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        from PIL import Image
        item = self.samples[i]
        name = item["image"] if isinstance(item["image"], str) else item.get("screenshot", "")
        if not name:
            name = "frame_0.png"
        img_path = os.path.join(_here, "control_data", "screenshots", os.path.basename(name))
        if not os.path.isfile(img_path):
            img_path = os.path.join(_here, "control_data", "screenshots", name)
        img = Image.open(img_path).convert("RGB")
        img = img.resize(self.image_size, Image.Resampling.LANCZOS)
        arr = np.array(img).astype(np.float32) / 255.0
        # NCHW for PyTorch
        arr = np.transpose(arr, (2, 0, 1))
        target = np.array(item["target"], dtype=np.float32)
        # -1 表示未标注，loss 时 mask 掉
        return torch.from_numpy(arr), torch.from_numpy(target)


class WeChatCNN(nn.Module):
    """小 CNN：输入 3x224x224，输出 2*K 的回归值 (0~1)。"""
    def __init__(self, num_controls=5, out_dim=None):
        super().__init__()
        if out_dim is None:
            out_dim = num_controls * 2
        self.out_dim = out_dim
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 5, stride=2, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, out_dim),
            nn.Sigmoid(),  # 输出 0~1
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


def train_epoch(model, loader, criterion, optimizer, device, mask_invalid=True):
    model.train()
    total_loss = 0.0
    n = 0
    for imgs, targets in loader:
        imgs, targets = imgs.to(device), targets.to(device)
        optimizer.zero_grad()
        out = model(imgs)
        if mask_invalid:
            mask = (targets >= 0).float()
            loss = (criterion(out, targets) * mask).sum() / (mask.sum() + 1e-6)
        else:
            loss = criterion(out, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n += 1
    return total_loss / n if n else 0


def main():
    if not HAS_TORCH:
        print("需要安装 PyTorch: pip install torch")
        return
    train_list = os.path.join(DATASET_DIR, "train_list.json")
    val_list = os.path.join(DATASET_DIR, "val_list.json")
    if not os.path.isfile(train_list):
        print("请先运行: python dataset_cnn.py 生成数据集（并确保 record_controls 已录过几帧）")
        return
    with open(os.path.join(DATASET_DIR, "meta.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    control_order = meta.get("control_order", ["search_box", "input_box", "chat_history", "contacts_list"])
    image_size = tuple(meta.get("image_size", [224, 224]))
    out_dim = len(control_order) * 2

    train_ds = WeChatControlDataset(train_list, image_size=image_size, control_order=control_order)
    val_ds = WeChatControlDataset(val_list, image_size=image_size, control_order=control_order) if os.path.isfile(val_list) else None
    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=8, num_workers=0) if val_ds and len(val_ds) else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = WeChatCNN(num_controls=len(control_order), out_dim=out_dim).to(device)
    criterion = nn.MSELoss(reduction="none")
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    epochs = 30
    best_val = float("inf")
    for ep in range(epochs):
        train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss = None
        if val_loader:
            model.eval()
            v = 0.0
            cnt = 0
            with torch.no_grad():
                for imgs, targets in val_loader:
                    imgs, targets = imgs.to(device), targets.to(device)
                    out = model(imgs)
                    mask = (targets >= 0).float()
                    loss = (criterion(out, targets) * mask).sum() / (mask.sum() + 1e-6)
                    v += loss.item()
                    cnt += 1
            val_loss = v / cnt if cnt else 0
            if val_loss < best_val:
                best_val = val_loss
                torch.save({"model": model.state_dict(), "control_order": control_order, "image_size": image_size}, os.path.join(MODEL_DIR, "best.pt"))
        print(f"epoch {ep+1} train_loss={train_loss:.4f}" + (f" val_loss={val_loss:.4f}" if val_loss is not None else ""))
    torch.save({"model": model.state_dict(), "control_order": control_order, "image_size": image_size}, os.path.join(MODEL_DIR, "last.pt"))
    print("模型已保存到", MODEL_DIR)


if __name__ == "__main__":
    main()
