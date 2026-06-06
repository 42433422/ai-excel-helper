"""
AI 引擎层

提供各种 AI 模型的推理服务，包括：
- BERT 意图分类
- DeepSeek 意图识别
- RASA NLU
- 蒸馏模型
- 模型训练器
"""

try:
    from app.ai_engines.bert import BertIntentClassifier
except ModuleNotFoundError:
    BertIntentClassifier = None  # type: ignore[misc, assignment]

__all__ = [
    "BertIntentClassifier",
]
