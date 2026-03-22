# RASA 意图识别集成计划

## 一、现有系统分析

### 1.1 当前意图识别方式
- **纯规则匹配**：基于关键词、否定前缀/短语、优先级排序
- **优点**：速度快、可解释、无需训练
- **缺点**：难以处理变体表达、口语化、拼写错误

### 1.2 现有模块结构
```
intent_service.py
├── TOOL_INTENTS (工具意图定义)
├── HINT_ONLY_INTENTS (仅提示意图)
├── NEGATION_PREFIXES / NEGATION_PHRASES (否定检测)
├── GREETING_PATTERNS / GOODBYE_PATTERNS (特殊意图)
├── recognize_intents() - 主入口函数
└── get_tool_key_with_negation_check() - 简化接口
```

---

## 二、RASA 集成方案

### 2.1 推荐方案：混合架构（规则 + RASA）

**核心思路**：
- RASA 作为**第一层 NLU 引擎**，处理变体表达和模糊意图
- 现有规则系统作为**第二层校验层**，处理业务逻辑和否定检测
- 两者结合，兼顾准确性和灵活性

```
用户消息
    │
    ▼
┌─────────────────┐
│  RASA NLU       │  ← 处理变体表达、口语化、拼写容错
│  (意图分类)      │
└────────┬────────┘
         │ intent + confidence
         ▼
┌─────────────────┐
│ 规则系统校验     │  ← 否定检测、特殊格式、业务逻辑
│  (二次校验)      │
└────────┬────────┘
         │
         ▼
    最终意图输出
```

### 2.2 RASA 优势

| 能力 | 说明 |
|------|------|
| **意图分类** | 支持同义词、变体表达自动识别 |
| **实体抽取** | 可提取产品名、数量、规格等业务实体 |
| **置信度** | 提供分类置信度，可设置阈值 |
| **增量训练** | 可不断添加训练数据提升准确率 |
| **上下文** | 支持对话上下文（slots, forms） |

---

## 三、集成步骤

### 步骤 1：环境准备

```bash
# 安装 RASA Open Source
pip install rasa

# 或仅安装 RASA NLU（轻量版）
pip install rasa-model-server  # 或使用独立模型
```

### 步骤 2：创建 RASA NLU 配置

**文件：** `e:\FHD\XCAGI\rasa\config.yml`

```yaml
language: zh

pipeline:
  - name: ChineseTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: DIETClassifier
    epochs: 100
    intent_classification: true
    entity_recognition: true
```

### 步骤 3：定义训练数据

**文件：** `e:\FHD\XCAGI\rasa\data\nlu.yml`

```yaml
version: "3.1"

nlu:
# 发货单生成
- intent: shipment_generate
  examples: |
    - 生成发货单
    - 开发货单
    - 开个单
    - 打单
    - 帮我开个发货单
    - 做一份送货单

# 客户查询
- intent: customers
  examples: |
    - 查看客户列表
    - 客户有哪些
    - 顾客名单
    - 单位列表

# 产品查询
- intent: products
  examples: |
    - 产品有哪些
    - 查看产品
    - 商品列表
    - 产品规格

# 微信发送
- intent: wechat_send
  examples: |
    - 发给他
    - 发送消息
    - 发微信
    - 发给客户

# 打印标签
- intent: print_label
  examples: |
    - 打印标签
    - 打标签
    - 标签打印

# 问候
- intent: greet
  examples: |
    - 你好
    - 您好
    - 嗨
    - 在吗

# 否定测试
- intent: negation_test
  examples: |
    - 不要生成
    - 别打印
    - 不用开单
```

### 步骤 4：创建领域定义

**文件：** `e:\FHD\XCAGI\rasa\domain.yml`

```yaml
version: "3.1"

intents:
  - shipment_generate
  - customers
  - products
  - wechat_send
  - print_label
  - upload_file
  - shipments
  - materials
  - greet
  - goodbye
  - help

responses:
  utter_greet:
    - text: "您好！有什么可以帮您的？"

  utter_goodbye:
    - text: "再见，有需要随时找我！"
```

### 步骤 5：训练 RASA 模型

```bash
cd e:\FHD\XCAGI\rasa
rasa train nlu
```

### 步骤 6：创建 RASA 服务包装类

**新文件：** `e:\FHD\XCAGI\app\services\rasa_nlu_service.py`

```python
# -*- coding: utf-8 -*-
"""RASA NLU 服务包装"""

import asyncio
import requests
from typing import Dict, Any, Optional

class RasaNLUService:
    def __init__(self, rasa_url: str = "http://localhost:5005"):
        self.rasa_url = rasa_url
        self.rasa_model = "default"

    async def parse(self, message: str) -> Dict[str, Any]:
        """调用意图识别"""
        try:
            response = requests.post(
                f"{self.rasa_url}/model/parse",
                json={"text": message, "model": self.rasa_model},
                timeout=5
            )
            return response.json()
        except Exception as e:
            return {"intent": None, "error": str(e)}

    def get_intent_with_confidence(self, message: str) -> tuple:
        """获取意图和置信度"""
        result = asyncio.run(self.parse(message))
        if result.get("intent"):
            return result["intent"]["name"], result["intent"]["confidence"]
        return None, 0.0
```

### 步骤 7：修改意图识别服务

**修改文件：** `e:\FHD\XCAGI\app\services\intent_service.py`

```python
# -*- coding: utf-8 -*-
"""混合意图识别服务：规则 + RASA"""

from typing import Dict, Any, Optional
from .rasa_nlu_service import RasaNLUService

# 现有规则系统保持不变...

class HybridIntentService:
    def __init__(self, use_rasa: bool = True):
        self.rule_service = IntentService()  # 现有规则服务
        self.rasa_service = RasaNLUService() if use_rasa else None
        self.rasa_confidence_threshold = 0.7

    async def recognize(self, message: str) -> Dict[str, Any]:
        """混合意图识别"""

        # 1. 规则系统快速识别
        rule_result = self.rule_service.recognize_intents(message)

        # 2. RASA NLU 识别（如果启用）
        rasa_intent = None
        rasa_confidence = 0.0

        if self.rasa_service:
            rasa_result = await self.rasa_service.parse(message)
            if rasa_result.get("intent"):
                rasa_intent = rasa_result["intent"]["name"]
                rasa_confidence = rasa_result["intent"]["confidence"]

        # 3. 结果融合
        if rasa_intent and rasa_confidence >= self.rasa_confidence_threshold:
            # RASA 高置信度，采用 RASA 结果
            rule_result["rasa_intent"] = rasa_intent
            rule_result["rasa_confidence"] = rasa_confidence

        return rule_result
```

---

## 四、集成模式选择

### 模式 A：RASA Embedded（推荐小型系统）

RASA 作为 Python 库直接调用，无需单独服务

```bash
pip install rasa
```

```python
from rasa.model import unpack_model
from rasa.core.agent import Agent

agent = Agent.load("models/nlu-20240601-xxxx.tar.gz")
result = await agent.parse_message("生成发货单")
```

### 模式 B：RASA Server（推荐生产环境）

启动独立 RASA 服务，通过 HTTP 调用

```bash
rasa run --enable-api --models models/
```

```python
requests.post("http://localhost:5005/model/parse", json={"text": "生成发货单"})
```

---

## 五、实施时间估算

| 步骤 | 内容 | 复杂度 |
|------|------|--------|
| 1 | 环境准备 | 低 |
| 2 | NLU 配置 | 低 |
| 3 | 训练数据迁移 | 中 |
| 4 | 领域定义 | 低 |
| 5 | 模型训练 | 中 |
| 6 | 服务包装类 | 中 |
| 7 | 集成测试 | 中 |

---

## 六、注意事项

### 6.1 RASA 中文支持
- 需要使用中文 tokenizer（如 `JiebaTokenizer`）
- 或使用预训练中文模型

### 6.2 训练数据量
- 建议每个意图至少 10-20 条样本
- 覆盖同义词、变体、口语化表达

### 6.3 否定检测保留
- RASA 意图识别不擅长处理否定
- 否定检测必须保留在规则层

### 6.4 性能考虑
- RASA 模型推理约 50-100ms
- 可考虑缓存、模型优化

---

## 七、替代方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **RASA** | 功能完整、NLU强大 | 重量级、需训练 | 复杂对话系统 |
| **DMIPL** | 轻量、中文优化 | 生态较小 | 简单对话 |
| ** transformers + Intent** | 效果最好 | 需GPU、资源高 | 高精度需求 |
| **保持现有规则** | 简单、可控 | 扩展性差 | 意图固定场景 |

---

## 八、建议的实施路径

1. **Phase 1**：创建 RASA NLU 配置和训练数据
2. **Phase 2**：训练 RASA 模型并验证效果
3. **Phase 3**：实现混合识别服务
4. **Phase 4**：A/B 测试对比效果
5. **Phase 5**：根据数据迭代优化
