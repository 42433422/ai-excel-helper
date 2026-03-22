# -*- coding: utf-8 -*-
"""
BERT 意图分类推理服务

基于预训练 Transformer 模型的意图识别推理
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
    """
    BERT 意图分类器

    支持：
    - 加载预训练的 BERT 模型
    - 意图分类推理
    - 置信度阈值控制
    - 与规则系统混合使用
    """

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
        """
        初始化 BERT 意图分类器

        Args:
            model_path: 本地模型路径 (优先使用)
            model_name: 预训练模型名称
            max_length: 最大序列长度
            confidence_threshold: 置信度阈值
            device: 运行设备 (cuda/cpu)
            use_fp16: 是否使用半精度
            local_files_only: 是否仅使用本地文件
        """
        self.max_length = max_length
        self.confidence_threshold = confidence_threshold
        self.use_fp16 = use_fp16 and torch.cuda.is_available()
        self.local_files_only = local_files_only

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model = None
        self.tokenizer = None
        self.id2label = ID_TO_LABEL.copy()
        self.label2id = LABEL_TO_ID.copy()

        if model_path and os.path.exists(model_path):
            self._load_model(model_path, local_files_only=True)
        elif local_files_only:
            logger.info("local_files_only=True 且未提供有效模型路径，使用虚拟模型")
            self._setup_dummy_model()
        else:
            logger.info(f"本地模型未找到，将尝试加载在线模型 {model_name}")
            if model_name in self.DEFAULT_MODELS:
                actual_name = self.DEFAULT_MODELS[model_name]
            else:
                actual_name = model_name
            try:
                self._load_model(actual_name, local_files_only=False)
            except Exception as e:
                logger.warning(f"无法加载模型 {actual_name}: {e}")
                self._setup_dummy_model()

    def _load_model(self, model_path: str, local_files_only: bool = False):
        """加载模型和分词器
        
        Args:
            model_path: 模型路径或模型名称
            local_files_only: 是否仅使用本地文件
        """
        model_path = str(model_path)
        is_local_distillation_model = False

        if os.path.isdir(model_path):
            config_path = os.path.join(model_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "id2label" in config:
                        loaded_id2label = {int(k): v for k, v in config["id2label"].items()}
                        if "LABEL_0" in loaded_id2label.values():
                            is_local_distillation_model = True
                            logger.info("检测到蒸馏模型，使用标准意图标签映射")
                            self.id2label = ID_TO_LABEL.copy()
                            self.label2id = LABEL_TO_ID.copy()
                        else:
                            self.id2label = loaded_id2label
                            self.label2id = {v: int(k) for k, v in config.get("label2id", {}).items()}
                    if "label2id" in config and not is_local_distillation_model:
                        self.label2id = {k: int(v) for k, v in config["label2id"].items()}
            else:
                labels_path = os.path.join(model_path, "intent_labels.json")
                if os.path.exists(labels_path):
                    with open(labels_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.id2label = {int(k): v for k, v in data.get("id2label", {}).items()}
                        self.label2id = data.get("label2id", {})

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, 
            local_files_only=local_files_only
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_path, 
            local_files_only=local_files_only
        )
        self.model.to(self.device)
        self.model.eval()

        if self.use_fp16:
            self.model = self.model.half()

        logger.info(f"模型已加载：{model_path}, 设备：{self.device}, local_files_only={local_files_only}")

    def _setup_dummy_model(self):
        """设置虚拟模型（用于演示或测试）"""
        logger.warning("使用虚拟模型，仅返回随机结果")
        self.model = None
        self.tokenizer = None

    @torch.no_grad()
    def predict(self, text: str, return_probs: bool = False) -> Dict[str, Any]:
        """
        预测单个文本的意图

        Args:
            text: 输入文本
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果字典
        """
        if self.model is None or self.tokenizer is None:
            return self._dummy_predict(text, return_probs)

        inputs = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        if self.use_fp16:
            inputs = {k: v.half() for k, v in inputs.items()}

        outputs = self.model(**inputs)
        logits = outputs.logits

        probs = torch.softmax(logits, dim=-1)
        confidence, predicted_idx = torch.max(probs, dim=-1)

        predicted_idx = predicted_idx.item()
        confidence = confidence.item()

        predicted_label = self.id2label.get(predicted_idx, "unk")

        result = {
            "text": text,
            "intent": predicted_label,
            "confidence": round(confidence, 4),
            "model": "bert_intent_classifier",
        }

        if return_probs:
            prob_list = probs.squeeze().cpu().numpy().tolist()
            result["all_probs"] = {
                self.id2label.get(i, f"label_{i}"): round(float(p), 4)
                for i, p in enumerate(prob_list)
                if float(p) > 0.001
            }

        return result

    @torch.no_grad()
    def predict_batch(self, texts: List[str], return_probs: bool = False) -> List[Dict[str, Any]]:
        """
        批量预测文本的意图

        Args:
            texts: 输入文本列表
            return_probs: 是否返回所有类别的概率

        Returns:
            预测结果列表
        """
        if self.model is None or self.tokenizer is None:
            return [self._dummy_predict(text, return_probs) for text in texts]

        inputs = self.tokenizer(
            texts,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        if self.use_fp16:
            inputs = {k: v.half() for k, v in inputs.items()}

        outputs = self.model(**inputs)
        logits = outputs.logits

        probs = torch.softmax(logits, dim=-1)
        confidences, predicted_indices = torch.max(probs, dim=-1)

        results = []
        for i, text in enumerate(texts):
            predicted_idx = predicted_indices[i].item()
            confidence = confidences[i].item()
            predicted_label = self.id2label.get(predicted_idx, "unk")

            result = {
                "text": text,
                "intent": predicted_label,
                "confidence": round(confidence, 4),
                "model": "bert_intent_classifier",
            }

            if return_probs:
                prob_list = probs[i].cpu().numpy().tolist()
                result["all_probs"] = {
                    self.id2label.get(j, f"label_{j}"): round(float(p), 4)
                    for j, p in enumerate(prob_list)
                    if float(p) > 0.001
                }

            results.append(result)

        return results

    def _dummy_predict(self, text: str, return_probs: bool = False) -> Dict[str, Any]:
        """虚拟预测（当模型不可用时）"""
        import random

        intent = random.choice(INTENT_LABELS[:-1])
        confidence = round(random.uniform(0.5, 0.9), 4)

        result = {
            "text": text,
            "intent": intent,
            "confidence": confidence,
            "model": "dummy",
        }

        if return_probs:
            result["all_probs"] = {label: round(random.random() * 0.3, 4) for label in INTENT_LABELS}
            result["all_probs"][intent] = confidence

        return result

    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self.model is not None and self.tokenizer is not None


class BertIntentService:
    """
    BERT 意图识别服务

    管理 BERT 意图分类器，提供：
    - 单例模式
    - 与规则系统混合
    - 置信度自适应
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "bert-base-chinese",
        confidence_threshold: float = 0.7,
        use_fallback: bool = True,
        local_files_only: bool = False,
    ):
        """
        初始化 BERT 意图服务

        Args:
            model_path: 本地模型路径
            model_name: 预训练模型名称
            confidence_threshold: 置信度阈值
            use_fallback: 置信度不足时是否回退
            local_files_only: 是否仅使用本地文件
        """
        self.classifier = BertIntentClassifier(
            model_path=model_path,
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            local_files_only=local_files_only,
        )
        self.confidence_threshold = confidence_threshold
        self.use_fallback = use_fallback

    def recognize(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        识别文本意图

        Args:
            text: 输入文本
            context: 上下文信息

        Returns:
            意图识别结果
        """
        if not self.classifier.is_available() and not self.use_fallback:
            return {
                "intent": None,
                "confidence": 0.0,
                "source": "unavailable",
                "error": "模型不可用且未启用回退",
            }

        result = self.classifier.predict(text, return_probs=True)

        if result["confidence"] < self.confidence_threshold and self.use_fallback:
            result["source"] = "bert_low_confidence"
            result["fallback_recommended"] = True
        else:
            result["source"] = "bert"

        return result

    def recognize_batch(
        self, texts: List[str], context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """批量识别意图"""
        if not self.classifier.is_available() and not self.use_fallback:
            return [
                {"intent": None, "confidence": 0.0, "source": "unavailable"}
                for _ in texts
            ]

        results = self.classifier.predict_batch(texts, return_probs=True)

        for result in results:
            if result["confidence"] < self.confidence_threshold and self.use_fallback:
                result["source"] = "bert_low_confidence"
                result["fallback_recommended"] = True
            else:
                result["source"] = "bert"

        return results

    def get_top_intents(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        获取 Top-K 可能的意图

        Args:
            text: 输入文本
            top_k: 返回数量

        Returns:
            [(意图，置信度), ...] 列表
        """
        if not self.classifier.is_available():
            return []

        result = self.classifier.predict(text, return_probs=True)
        all_probs = result.get("all_probs", {})

        sorted_intents = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents[:top_k]


_bert_intent_service: Optional[BertIntentService] = None


def get_bert_intent_service(
    model_path: Optional[str] = None,
    model_name: str = "bert-base-chinese",
    confidence_threshold: float = 0.7,
    use_fallback: bool = True,
    local_files_only: bool = False,
) -> BertIntentService:
    """
    获取 BERT 意图服务单例

    Args:
        model_path: 本地模型路径
        model_name: 预训练模型名称
        confidence_threshold: 置信度阈值
        use_fallback: 是否使用回退
        local_files_only: 是否仅使用本地文件

    Returns:
        BertIntentService 实例
    """
    global _bert_intent_service

    if _bert_intent_service is None:
        _bert_intent_service = BertIntentService(
            model_path=model_path,
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            use_fallback=use_fallback,
            local_files_only=local_files_only,
        )

    return _bert_intent_service


def reset_bert_intent_service():
    """重置 BERT 意图服务单例"""
    global _bert_intent_service
    _bert_intent_service = None
