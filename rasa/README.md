# RASA NLU 意图识别模块

本模块提供基于 RASA 的意图识别能力，与现有的规则系统结合形成混合意图识别服务。

## 目录结构

```
rasa/
├── config.yml          # RASA NLU 配置
├── domain.yml          # RASA 领域定义
├── data/
│   └── nlu.yml         # NLU 训练数据
├── models/             # 训练生成的模型目录
└── train_rasa_model.py # 模型训练脚本
```

## 快速开始

### 1. 安装 RASA

```bash
pip install rasa
```

### 2. 训练模型

```bash
cd e:\FHD\XCAGI
python rasa/train_rasa_model.py
```

### 3. 使用混合意图识别

```python
from app.services import hybrid_recognize_intents

result = hybrid_recognize_intents("生成发货单")
print(result)
```

## 集成模式

### 模式 A: 嵌入式（推荐小型系统）

```python
from app.services import RasaNLUService

service = RasaNLUService(model_path="rasa/models/nlu-20240101-xxxx.tar.gz")
result = service.get_intent_with_confidence("生成发货单")
```

### 模式 B: 服务器模式（生产环境）

```bash
# 启动 RASA 服务器
rasa run --enable-api --models rasa/models/
```

```python
from app.services import RasaNLUService

service = RasaNLUService(rasa_url="http://localhost:5005", use_server=True)
result = service.get_intent_with_confidence("生成发货单")
```

## 训练数据格式

NLU 训练数据使用 RASA 3.x 格式:

```yaml
version: "3.1"

nlu:
- intent: intent_name
  examples: |
    - 示例1
    - 示例2
    - 示例3
```

## 意图映射

RASA 意图与系统意图的映射关系:

| RASA Intent | System Intent |
|-------------|----------------|
| shipment_generate | shipment_generate |
| customers | customers |
| products | products |
| wechat_send | wechat_send |
| print_label | print_label |
| upload_file | upload_file |
| materials | materials |
| shipment_template | shipment_template |
| greet | greet |
| goodbye | goodbye |
| help | help |
| negation_test | negation |

## 置信度阈值

默认置信度阈值为 0.7，低于该阈值的 RASA 识别结果将被忽略，仍使用规则系统的结果。

## 注意事项

1. **中文分词**: 使用 JiebaTokenizer 进行中文分词
2. **否定检测**: 否定检测仍在规则层处理，RASA 识别结果中的否定会被过滤
3. **性能**: RASA 模型推理约 50-100ms，可考虑缓存优化
4. **训练数据**: 建议每个意图至少 10-20 条样本，覆盖同义词和变体表达
