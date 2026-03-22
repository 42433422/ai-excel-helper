# 微信搜索框 YOLO 检测

当 OCR/cv2 识别搜索框不稳定时，可用自训练 YOLO 模型优先定位搜索框。

## 1. 采集标注

1. 打开微信 PC 主窗口。
2. 运行：
   ```bash
   cd wechat_cv
   python collect_search_box_labels.py
   ```
3. 在弹窗里用鼠标**拖拽框选搜索框**（绿色框），按 **s** 保存。
4. 多换几种窗口大小、缩放比例，采集 **10～20 张** 后按 **q** 退出。

标注会保存在 `wechat_cv/yolo_search_dataset/images` 和 `labels/`。

## 2. 训练

```bash
cd wechat_cv
python train_wechat_yolo.py
```

首次运行会下载 `yolov8n.pt`。训练结束后会把 `wechat_ui.pt` 生成到当前目录。

## 3. 使用

把生成的 **wechat_ui.pt** 放在 `wechat_cv` 目录下（或设置环境变量 `WECHAT_YOLO_MODEL=路径/wechat_ui.pt`）。  
之后「打开对话框」等流程会**优先用 YOLO 找搜索框**，找不到再退回到 OCR / 模板匹配 / 比例 fallback。

## 依赖

- `opencv-python`、`numpy`（采集）
- `ultralytics>=8.0`（训练与推理）
