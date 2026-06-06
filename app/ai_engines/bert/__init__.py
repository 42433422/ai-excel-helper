"""
BERT 意图分类服务

此模块已迁移到 app/ai_engines/bert/
"""

try:
    from app.ai_engines.bert.intent_service import BertIntentClassifier
except ModuleNotFoundError as exc:
    if exc.name != "transformers":
        raise

    class BertIntentClassifier:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.available = False

        def is_available(self) -> bool:
            return False

        def classify(self, *args, **kwargs):
            return []

        def predict(self, *args, **kwargs):
            return []


__all__ = ["BertIntentClassifier"]
