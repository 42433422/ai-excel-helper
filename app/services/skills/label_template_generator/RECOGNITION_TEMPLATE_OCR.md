# 识别模板（图片标签）与 OCR 的关系

## 前端/路由入口

- 控制台 **模板预览 / 新建模板** 上传图片（`.png` / `.jpg` / …）时，会请求后端 **`POST .../templates/analyze`**（蓝图 `templates_bp`）。
- 路由：`app/routes/templates.py` → `analyze_template()` → **`_analyze_label_template()`**

## OCR 实现（已与 `/api/ocr` 统一）

- `_analyze_label_template` 调用 **`LabelTemplateGeneratorSkill.execute(..., enable_ocr=True)`**  
  实现文件：**`app/services/skills/label_template_generator/label_template_generator.py`**
- 文字识别：**`extract_text_with_ocr()`** 通过 **`get_ocr_service().recognize_text_blocks(img)`** 取带坐标的文本块，与 **`/api/ocr`**、`recognize_file` 等使用同一 **`OCRService`**。
- **默认优先 PaddleOCR**（`app/services/paddle_ocr_runner.py` 进程内单例）；未安装或初始化失败时按 **`XCAGI_OCR_BACKEND`** 回退 **EasyOCR** / **Tesseract**（与 `ocr_service.py` 一致）。
- **表格线网格**：仍在 `extract_text_with_ocr` 内用 **OpenCV** 检测，与引擎无关。

### 环境变量

| 变量 | 说明 |
|------|------|
| `XCAGI_OCR_BACKEND` | `auto`（默认）、`paddle`、`easyocr`、`tesseract` |
| `PADDLEOCR_LANG` | Paddle 语言，默认 `ch` |
| `XCAGI_PADDLE_MODEL_ROOT` | 本地推理模型根目录（见下「离线模型」） |
| `PADDLEOCR_TEXT_DET_MODEL_DIR` / `PADDLEOCR_TEXT_REC_MODEL_DIR` | 分别指定 det/rec 目录（须含 `inference.yml`，优先级高于 `XCAGI_PADDLE_MODEL_ROOT`） |
| `PADDLEOCR_TEXT_DET_MODEL_NAME` / `PADDLEOCR_TEXT_REC_MODEL_NAME` | 与目录内 yaml 中 `Global.model_name` 一致（默认 PP-OCRv4 mobile） |
| `PADDLE_PDX_MODEL_SOURCE` | 在线拉模时可选 `BOS`，优先走百度对象存储（国内网络更稳） |

### 离线模型（推荐内网部署）

1. 在有外网的机器上执行（或在服务器上若可访问 BOS）：

   `python scripts/download_paddleocr_ch_models.py`

   默认解压到 **`XCAGI/paddleocr_local_models/`**（可用 `--dir` 指定其它路径）。

2. 启动 XCAGI 前设置 **`XCAGI_PADDLE_MODEL_ROOT`** 为该目录（PowerShell：`$env:XCAGI_PADDLE_MODEL_ROOT="E:\FHD\XCAGI\paddleocr_local_models"`）。

3. 重启服务后，从该目录加载 **PP-OCRv4_mobile_det / PP-OCRv4_mobile_rec**（PaddleX 格式）；为减少联网依赖，当前实现**不启用**文档预处理与文字行方向子模型。

**注意**：旧版脚本下载的 `ch_PP-OCRv4_*`（仅 `pdmodel`，无 `inference.yml`）与 PaddleOCR 3.x 不兼容，请删除后改用当前 `scripts/download_paddleocr_ch_models.py`。

## 与旧文档的差异

历史上标签模板曾 **单独** `import PaddleOCR`。现已改为 **只通过 OCRService**，避免双份模型与行为不一致。

## 依赖

- 网格：**Pillow、numpy、opencv-python**
- OCR（推荐）：**paddlepaddle + paddleocr**；或 **easyocr**；或系统 **Tesseract** + **pytesseract**

## 相关代码位置（速查）

```
app/routes/templates.py          → analyze_template, _analyze_label_template
app/services/ocr_service.py      → OCRService（Paddle 优先）
app/services/paddle_ocr_runner.py → PaddleOCR 单例与 predict 解析
app/services/skills/label_template_generator/label_template_generator.py
  → extract_text_with_ocr, _pair_fields_by_grid, LabelTemplateGeneratorSkill.execute
app/routes/ocr.py                → /api/ocr/*
```
