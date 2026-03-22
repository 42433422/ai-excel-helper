# -*- coding: utf-8 -*-
"""
BERT 意图分类推理服务

基于预训练 Transformer 模型的意图识别推理

原始模块位于 app/services/bert_intent_service.py
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BertTokenizer,
)

logger = logging.getLogger(__name__)


INTENT_LABELS = [
    "shipment_generate",
    "customers",
    "products",
    "shipments",
    "wechat_send",
    "print_label",
    "upload_file",
    "materials",
    "shipment_template",
    "excel_decompose",
    "show_images",
    "show_videos",
    "greet",
    "goodbye",
    "help",
    "negation",
    "customer_export",
    "customer_edit",
    "customer_supplement",
    "unk",
]

LABEL_TO_ID = {label: idx for idx, label in enumerate(INTENT_LABELS)}
ID_TO_LABEL = {idx: label for idx, label in enumerate(INTENT_LABELS)}


class BertIntentClassifier:
    DEFAULT_MODELS = {
        "bert-base-chinese": "bert-base-chinese",
        "chinese-bert-wwm": "hfl/chinese-bert-wwm-ext",
        "chinese-roberta": "hfl/chinese-roberta-wwm-ext",
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "bert-base-chinese",
        max_length: int = 64,
        confidence_threshold: float = 0.7,
        device: Optional[str] = None,
        use_fp16: bool = False,
        local_files_only: bool = False,
    ):
        self.model_path = model_path
        self.model_name = model_name
        self.max_length = max_length
        self.confidence_threshold = confidence_threshold
        self.use_fp16 = use_fp16
        self.local_files_only = local_files_only

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model = None
        self.tokenizer = None
        self._initialized = False

    def load_model(self) -> bool:
        if self._initialized:
            return True

        try:
            if self.model_path and os.path.exists(self.model_path):
                logger.info(f"加载 BERT 模型：{self.model_path}, 设备：{self.device}")

                config = AutoConfig.from_pretrained(
                    self.model_path,
                    num_labels=len(INTENT_LABELS),
                    local_files_only=self.local_files_only,
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_path,
                    config=config,
                    local_files_only=self.local_files_only,
                )
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    local_files_only=self.local_files_only,
                )
            else:
                default_model = self.DEFAULT_MODELS.get(self.model_name, self.model_name)
                logger.info(f"加载默认 BERT 模型：{default_model}, 设备：{self.device}")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    default_model,
                    num_labels=len(INTENT_LABELS),
                    local_files_only=self.local_files_only,
                )
                self.tokenizer = BertTokenizer.from_pretrained(
                    default_model,
                    local_files_only=self.local_files_only,
                )

            self.model.to(self.device)
            self.model.eval()

            if self.use_fp16:
                self.model.half()

            self._initialized = True
            logger.info("BERT 模型加载成功")
            return True

        except Exception as e:
            logger.error(f"BERT 模型加载失败：{e}")
            return False

    def predict(self, text: str) -> Dict[str, Any]:
        if not self._initialized:
            self.load_model()

        if not text or not text.strip():
            return {"intent": "unk", "confidence": 0.0, "probabilities": {}}

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=self.max_length,
                truncation=True,
                padding="max_length",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            probs = torch.softmax(logits, dim=-1)[0]
            confidence, predicted_idx = torch.max(probs, dim=-1)

            predicted_idx = predicted_idx.item()
            confidence = confidence.item()

            predicted_label = ID_TO_LABEL.get(predicted_idx, "unk")

            if confidence < self.confidence_threshold:
                predicted_label = "unk"

            result = {
                "intent": predicted_label,
                "confidence": round(confidence, 4),
                "predicted_idx": predicted_idx,
                "text": text,
            }

            return result

        except Exception as e:
            logger.error(f"BERT 预测失败：{e}")
            return {"intent": "unk", "confidence": 0.0, "error": str(e)}

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        if not self._initialized:
            self.load_model()

        return [self.predict(text) for text in texts]
