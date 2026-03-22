# -*- coding: utf-8 -*-
"""
蒸馏模型意图识别服务

使用微调后的本地 BERT 模型进行意图识别，作为 DeepSeek API 的替代方案。
降低 API 调用成本，提高响应速度。

使用方式：
1. 训练蒸馏模型：python -m app.services.distillation_trainer --data distillation/training_data.jsonl --epochs 3
2. 启动服务时设置环境变量：USE_DISTILLED_MODEL=1
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "distillation", "checkpoints")

DEFAULT_INTENT_LABELS = [
    "shipment_generate", "customers", "products", "shipments",
    "wechat_send", "print_label", "upload_file", "materials",
    "shipment_template", "excel_decompose", "show_images", "show_videos",
    "greet", "goodbye", "help", "negation", "customer_export",
    "customer_edit", "customer_supplement", "unk"
]


class DistilledIntentRecognizer:
    """蒸馏模型意图识别器"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.model_path = model_path or os.path.join(CHECKPOINT_DIR, "best.pt")
        self.model = None
        self.tokenizer = None
        self.id2label = None
        self.label2id = None
        self._initialized = False

        self._load_model()

    def _load_model(self):
        """加载蒸馏模型"""
        if not os.path.exists(self.model_path):
            logger.warning(f"蒸馏模型不存在：{self.model_path}，将使用 fallback")
            self._initialized = True
            return

        try:
            import json

            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.id2label = None
            self.label2id = None
            
            config_path = os.path.join(self.model_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    raw_id2label = config.get("id2label", {})
                    raw_label2id = config.get("label2id", {})
                    
                    if raw_id2label and "LABEL_0" in raw_id2label.values():
                        logger.info("检测到蒸馏模型，使用标准意图标签映射")
                        self.id2label = {i: label for i, label in enumerate(DEFAULT_INTENT_LABELS)}
                        self.label2id = {v: k for k, v in self.id2label.items()}
                    else:
                        self.id2label = {int(k): v for k, v in raw_id2label.items()}
                        self.label2id = {v: int(k) for k, v in raw_label2id.items()}
            else:
                vocab_path = os.path.join(CHECKPOINT_DIR, "vocab.json")
                if os.path.exists(vocab_path):
                    with open(vocab_path, "r", encoding="utf-8") as f:
                        vocab = json.load(f)
                        raw_id2label = vocab.get("id2label", {})
                        if raw_id2label and "LABEL_0" in raw_id2label.values():
                            logger.info("检测到蒸馏模型，使用标准意图标签映射")
                            self.id2label = {i: label for i, label in enumerate(DEFAULT_INTENT_LABELS)}
                            self.label2id = {v: k for k, v in self.id2label.items()}
                        else:
                            self.id2label = {int(k): v for k, v in raw_id2label.items()}
                            self.label2id = vocab.get("label2id", {})

            if self.id2label is None:
                logger.warning("无法加载标签映射，使用默认标签")
                self.id2label = {i: label for i, label in enumerate(DEFAULT_INTENT_LABELS)}
                self.label2id = {v: k for k, v in self.id2label.items()}

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path, local_files_only=True
            )

            if os.environ.get("USE_CUDA", "0") == "1":
                import torch
                self.model = self.model.to("cuda")

            self.model.eval()

            logger.info(f"蒸馏模型加载成功：{self.model_path}")
            self._initialized = True

        except Exception as e:
            logger.error(f"加载蒸馏模型失败：{e}")
            self._initialized = True

    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self.model is not None and self.tokenizer is not None

    def recognize(self, text: str) -> Dict[str, Any]:
        """识别意图"""
        if not self.is_available():
            return {
                "intent": None,
                "confidence": 0.0,
                "slots": {},
                "reasoning": "蒸馏模型不可用",
                "source": "distilled_fallback"
            }

        import torch
        import torch.nn.functional as F

        try:
            inputs = self.tokenizer(
                text,
                max_length=128,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )

            if hasattr(self.model, "device"):
                device = self.model.device
                inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = F.softmax(logits, dim=-1)
                confidence, predicted_idx = torch.max(probs, dim=-1)

            predicted_idx = predicted_idx.item()
            confidence = confidence.item()
            predicted_label = self.id2label.get(predicted_idx, "unk")

            return {
                "intent": predicted_label,
                "confidence": round(confidence, 4),
                "slots": {},
                "reasoning": "蒸馏模型推理",
                "source": "distilled"
            }

        except Exception as e:
            logger.error(f"蒸馏模型推理失败：{e}")
            return {
                "intent": None,
                "confidence": 0.0,
                "slots": {},
                "reasoning": f"推理错误：{str(e)}",
                "source": "distilled_error"
            }


_distilled_recognizer: Optional[DistilledIntentRecognizer] = None


def get_distilled_recognizer(model_path: Optional[str] = None) -> DistilledIntentRecognizer:
    """获取蒸馏识别器单例"""
    global _distilled_recognizer
    if _distilled_recognizer is None:
        _distilled_recognizer = DistilledIntentRecognizer(model_path=model_path)
    return _distilled_recognizer


def is_distilled_model_available() -> bool:
    """检查蒸馏模型是否可用"""
    recognizer = get_distilled_recognizer()
    return recognizer.is_available()


def use_distilled_model() -> bool:
    """检查是否应该使用蒸馏模型"""
    if os.environ.get("USE_DISTILLED_MODEL", "0") == "1":
        return is_distilled_model_available()
    return False
