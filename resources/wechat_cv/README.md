# 微信纯 CV 发送（截图 + 点击/粘贴）

不依赖微信的 UI 控件树（pywinauto），用**截屏 + 可选 OCR** 理解界面，再用**点击 + 剪贴板粘贴**发送，适合 Qt 版 Weixin 或存在防护白幕的情况。

---

## CV 记录位置 → 怎么点击（流程说明）

### 记录时：CV 如何「看到」并得到点击位置

有两种方式，得到的都是**相对坐标 (rx, ry)，范围 0～1**（与窗口大小无关，便于窗口缩放后复用）。

| 方式 | 命令 | 过程 |
|------|------|------|
| **OCR 自动** | `python record_controls.py ocr` | 1. 截取微信窗口图 → 2. 用 EasyOCR 识别图中文字（如「搜索」「输入」「会话」）→ 3. 取每个匹配文字框的**中心**为 (cx, cy)，除以窗口宽高得到 (rx, ry) → 4. 按**区域约束**过滤（如「搜索」只在顶部、「输入」在底部），避免误匹配（如「发送视频」）→ 5. 写入 `control_data/control_positions.json` |
| **手动点击** | `python record_controls.py` | 1. 截取微信窗口图 → 2. 弹出 Tk 窗口显示该图（可能缩放过）→ 3. 你在图上**按顺序点击**各控件 → 4. 程序把点击的像素 (event.x, event.y) 按缩放比例还原为**窗口内像素**，再 `pixel_to_relative(px, py, rect)` 转为 (rx, ry) → 5. 写入同一 JSON |

核心函数（`record_controls.py`）：

- `pixel_to_relative(px, py, rect)`：窗口内像素 → 相对坐标 (0~1)
- `relative_to_pixel(rx, ry, rect)`：相对坐标 → 当前窗口的**屏幕像素** (px, py)

### 点击时：怎么用记录的位置点下去

所有「按记录点击」的脚本（如 `test_clicks.py`、`test_search_paste.py`）流程一致：

1. **读位置**：从 `control_positions.json` 取最新一帧或平均的 `positions`，例如 `{"search_box": [0.12, 0.04], ...}`。
2. **取当前窗口**：`_find_wechat_handle()` 找到微信窗口，`_window_rect(hwnd)` 得到当前窗口的 `rect = (x0, y0, w, h)`（屏幕坐标）。
3. **相对 → 屏幕**：对每个控件 `(rx, ry)` 调用 `relative_to_pixel(rx, ry, rect)` 得到该控件在当前窗口下的**屏幕坐标** `(px, py)`。
4. **点击**：`pyautogui.click(px, py)` 在系统层面点击该像素。

因此：**记录阶段用 CV（截屏 + OCR 或截屏 + 人在图上点）得到相对坐标；点击阶段用当前窗口 rect 把相对坐标转成屏幕坐标再点击。**

---

## 控件位置 + CNN 快速定位 + 点击验证（推荐流程）

为保证每次点击正确，可先**记录所有控件位置**，再**用 CNN 快速预测位置**，且**每次点击后做正确性测试**。

### 1. 记录控件位置

- 打开微信并置于前台，运行：
  ```bash
  cd E:\FHD\wechat_cv
  python record_controls.py
  ```
- 会弹出当前微信截屏，按提示**依次点击**各控件（搜索、聊天、输入框、发送等），程序保存为相对坐标到 `control_data/control_positions.json`。
- 建议多录几帧（不同窗口大小或不同界面状态），再执行一次 `record_controls.py` 继续追加。

### 2. 测试每次点击是否正确

- 用已记录位置（默认用所有帧平均）依次点击，并对**每次点击**做前后截图差异验证：
  ```bash
  python test_clicks.py
  ```
- 若某控件验证失败，可重新运行 `record_controls.py` 补录或修正该控件位置；`test_clicks.py latest` 使用最新一帧；`test_clicks.py no-verify` 仅点击不验证。

### 3. 制作数据集并训练 CNN

- 从已记录帧生成训练/验证集：
  ```bash
  python dataset_cnn.py
  ```
- 训练 CNN（需安装 PyTorch）：
  ```bash
  pip install torch
  python train_cnn.py
  ```
- 模型保存到 `model_cnn/best.pt`，用于后续快速预测控件位置。

### 4. 用 CNN 预测并点击（带验证）

- 截屏 → CNN 预测各控件相对坐标 → 依次点击，且**每次点击后做正确性验证**：
  ```bash
  python predict_cnn.py
  ```
- 不加参数时默认每次点击都会验证；加 `no-verify` 则只点击不验证。

以上流程保证：先有**人工标注的位置**，再**测试点击是否生效**，最后用 **CNN 快速定位** 并继续用验证保证正确性。

## 依赖

```bash
pip install pywin32 pyautogui Pillow
# 可选：中文 OCR，用于精确定位「搜索」「发送」按钮
pip install easyocr
```

不装 easyocr 时，会按窗口几何位置做启发式点击（输入框在下方居中、「发送」在右下附近）。

## 使用方式

### 1. 命令行测试（向当前聊天发一条）

先**手动打开与对方的聊天**，把微信窗口放在前台，然后：

```bash
cd E:\FHD\wechat_cv
python -c "from wechat_cv_send import send_to_current_chat_by_cv; print(send_to_current_chat_by_cv('你好'))"
```

或：

```bash
python wechat_cv_send.py 你好
```

### 2. 获取当前聊天信息（标题栏 OCR 二次确认 + 聊天区域 OCR）

进入某聊天后，用**标题栏区域 OCR** 读左上角联系人名，或对**聊天消息区域**做 OCR 获取可见文字：

- **当前联系人名称**（二次确认）：
  ```bash
  python wechat_cv_send.py get_contact
  ```
  返回示例：`{"success": true, "contact_name": "白龙马^_^李秋林", "source": "ocr_title"}`

- **当前可见聊天文字**（按行，尽力而为）：
  ```bash
  python wechat_cv_send.py get_messages [max_lines]
  ```
  返回示例：`{"success": true, "messages": ["你好", "在吗"], "source": "ocr_chat_body"}`

仅对**固定区域**（标题栏 / 聊天区）做 OCR，不读整屏，无需视觉大模型，速度快、实现简单。

### 3. Cursor MCP（纯 CV 工具）

在 Cursor 的 MCP 配置里增加一项（与原有 wechat 并存即可）：

```json
"wechat-cv": {
  "command": "C:\\Program Files\\Python311\\python.exe",
  "args": ["E:\\FHD\\wechat_cv\\run_mcp_cv.py"]
}
```

提供的工具：

- **wechat_cv_send_current**：向「当前已打开的聊天」发消息（参数：`message`，可选 `delay`）
- **wechat_cv_send_to_friend**：先搜索好友再发送（参数：`to_user`, `message`，可选 `delay`）
- **wechat_cv_get_current_contact**：获取当前聊天窗口左上角联系人名称（标题栏 OCR 二次确认）
- **wechat_cv_get_chat_messages**：对当前聊天区域 OCR，返回可见消息行（可选 `max_lines`）

流程：找窗口 → 截屏 → 可选 OCR 定位 → 点击 + 粘贴 + Alt+S 发送；获取信息时仅对标题栏/聊天区做区域 OCR。

## 注意

- 发送前请把**微信窗口置于前台**，并尽量**先手动打开目标聊天**再调 `wechat_cv_send_current`，更稳。
- 若出现大块白幕，可尝试只使用「当前聊天」发送，减少自动点击步骤。
