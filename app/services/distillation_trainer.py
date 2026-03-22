# -*- coding: utf-8 -*-
"""
蒸馏训练脚本 - 微调 BERT 模型用于意图识别

使用收集的蒸馏数据微调 chinese-bert-wwm-ext 模型。

使用方法：
    python -m app.services.distillation_trainer --data distillation/training_data.jsonl --epochs 3

模型输出：
    distillation/checkpoints/best.pt
    distillation/checkpoints/last.pt
    distillation/checkpoints/vocab.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AdamW,
    BertForSequenceClassification,
    BertTokenizer,
    get_linear_schedule_with_warmup,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DISTILL_DIR = os.path.join(BASE_DIR, "distillation")
CHECKPOINT_DIR = os.path.join(DISTILL_DIR, "checkpoints")
LOG_DIR = os.path.join(DISTILL_DIR, "logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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
ID_TO_LABEL = {idx: label for label, idx in LABEL_TO_ID.items()}


class DistillationDataset(Dataset):
    """蒸馏数据集"""

    def __init__(self, texts: List[str], labels: List[int], tokenizer: BertTokenizer, max_length: int = 64):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


class DistillationTrainer:
    """蒸馏训练器"""

    def __init__(
        self,
        model_name: str = "hfl/chinese-bert-wwm-ext",
        num_labels: int = len(INTENT_LABELS),
        max_length: int = 64,
        learning_rate: float = 2e-5,
        batch_size: int = 16,
        epochs: int = 3,
        warmup_ratio: float = 0.1,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.num_labels = num_labels
        self.max_length = max_length
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.warmup_ratio = warmup_ratio

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"使用设备: {self.device}")

        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)

        self.tokenizer = None
        self.model = None
        self.train_loader = None
        self.val_loader = None

    def load_data(self, data_path: str) -> Tuple[List[str], List[int]]:
        """加载训练数据"""
        texts = []
        labels = []

        if data_path.endswith(".jsonl"):
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    text = data.get("text", "")
                    label = data.get("label", "unk")

                    if label in LABEL_TO_ID:
                        texts.append(text)
                        labels.append(LABEL_TO_ID[label])
        elif data_path.endswith(".tsv"):
            with open(data_path, "r", encoding="utf-8") as f:
                next(f)
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        texts.append(parts[0])
                        label = parts[1]
                        if label in LABEL_TO_ID:
                            labels.append(LABEL_TO_ID[label])

        logger.info(f"加载数据: {len(texts)} 条")
        return texts, labels

    def prepare_data(self, texts: List[str], labels: List[int], val_ratio: float = 0.2):
        """准备训练和验证数据"""
        if len(set(labels)) >= 10 and len(texts) > 100:
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, labels, test_size=val_ratio, random_state=42, stratify=labels
            )
        else:
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, labels, test_size=val_ratio, random_state=42
            )

        logger.info(f"训练集: {len(train_texts)} 条, 验证集: {len(val_texts)} 条")

        self.tokenizer = BertTokenizer.from_pretrained(self.model_name)

        train_dataset = DistillationDataset(train_texts, train_labels, self.tokenizer, self.max_length)
        val_dataset = DistillationDataset(val_texts, val_labels, self.tokenizer, self.max_length)

        self.train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        self.val_loader = DataLoader(val_dataset, batch_size=self.batch_size)

        self.model = BertForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=self.num_labels,
        )
        self.model.to(self.device)

    def train_epoch(self, optimizer, scheduler) -> float:
        """训练一个 epoch"""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0

        for batch in self.train_loader:
            optimizer.zero_grad()

            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["labels"].to(self.device)

            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        avg_loss = total_loss / len(self.train_loader)
        accuracy = correct / total
        return avg_loss, accuracy

    @torch.no_grad()
    def evaluate(self) -> Dict[str, float]:
        """评估模型"""
        self.model.eval()
        total_loss = 0
        all_preds = []
        all_labels = []

        for batch in self.val_loader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch["attention_mask"].to(self.device)
            labels = batch["labels"].to(self.device)

            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

        avg_loss = total_loss / len(self.val_loader)
        accuracy = accuracy_score(all_labels, all_preds)

        return {
            "val_loss": avg_loss,
            "val_accuracy": accuracy,
            "preds": all_preds,
            "labels": all_labels,
        }

    def save_checkpoint(self, path: str, epoch: int, best: bool = False):
        """保存检查点"""
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)

        config = {
            "model_name": self.model_name,
            "num_labels": self.num_labels,
            "id2label": ID_TO_LABEL,
            "label2id": LABEL_TO_ID,
            "max_length": self.max_length,
            "epoch": epoch,
            "best": best,
            "saved_at": datetime.now().isoformat(),
        }

        with open(os.path.join(path, "train_config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        vocab_path = os.path.join(CHECKPOINT_DIR, "vocab.json")
        with open(vocab_path, "w", encoding="utf-8") as f:
            json.dump({"id2label": ID_TO_LABEL, "label2id": LABEL_TO_ID}, f, ensure_ascii=False)

        logger.info(f"保存检查点到: {path}")

    def train(self, data_path: str, output_dir: str = CHECKPOINT_DIR):
        """完整训练流程"""
        texts, labels = self.load_data(data_path)

        if len(texts) < 10:
            logger.error("训练数据不足，至少需要 10 条数据")
            return

        self.prepare_data(texts, labels)

        optimizer = AdamW(self.model.parameters(), lr=self.learning_rate, weight_decay=0.01)

        total_steps = len(self.train_loader) * self.epochs
        warmup_steps = int(total_steps * self.warmup_ratio)

        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
        )

        best_accuracy = 0
        best_epoch = 0

        for epoch in range(1, self.epochs + 1):
            logger.info(f"\n=== Epoch {epoch}/{self.epochs} ===")

            train_loss, train_acc = self.train_epoch(optimizer, scheduler)
            logger.info(f"训练损失: {train_loss:.4f}, 训练准确率: {train_acc:.4f}")

            eval_result = self.evaluate()
            logger.info(f"验证损失: {eval_result['val_loss']:.4f}, 验证准确率: {eval_result['val_accuracy']:.4f}")

            last_checkpoint = os.path.join(output_dir, "last.pt")
            self.save_checkpoint(last_checkpoint, epoch, best=False)

            if eval_result["val_accuracy"] > best_accuracy:
                best_accuracy = eval_result["val_accuracy"]
                best_epoch = epoch
                best_checkpoint = os.path.join(output_dir, "best.pt")
                self.save_checkpoint(best_checkpoint, epoch, best=True)

            unique_labels = sorted(set(eval_result["labels"]) | set(eval_result["preds"]))
            label_names = [ID_TO_LABEL[i] for i in unique_labels]
            report = classification_report(
                eval_result["labels"],
                eval_result["preds"],
                labels=unique_labels,
                target_names=label_names,
                zero_division=0,
            )
            logger.info(f"\n分类报告:\n{report}")

        logger.info(f"\n训练完成! 最佳验证准确率: {best_accuracy:.4f} (Epoch {best_epoch})")

        log_path = os.path.join(LOG_DIR, f"training_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "best_accuracy": best_accuracy,
                "best_epoch": best_epoch,
                "total_epochs": self.epochs,
                "data_path": data_path,
                "model_name": self.model_name,
            }, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="蒸馏训练工具")
    parser.add_argument("--data", type=str, default=None, help="训练数据路径")
    parser.add_argument("--model", type=str, default="hfl/chinese-bert-wwm-ext", help="预训练模型名称")
    parser.add_argument("--epochs", type=int, default=3, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=16, help="批大小")
    parser.add_argument("--lr", type=float, default=2e-5, help="学习率")
    parser.add_argument("--max_length", type=int, default=64, help="最大序列长度")
    parser.add_argument("--output", type=str, default=None, help="输出目录")

    args = parser.parse_args()

    data_path = args.data
    if data_path is None:
        data_path = os.path.join(DISTILL_DIR, "training_data.jsonl")

    if not os.path.exists(data_path):
        logger.error(f"训练数据不存在: {data_path}")
        logger.info("请先运行数据采集脚本: python -m app.services.distillation_data_collector --generate --collect")
        return

    output_dir = args.output or CHECKPOINT_DIR

    trainer = DistillationTrainer(
        model_name=args.model,
        max_length=args.max_length,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        epochs=args.epochs,
    )

    trainer.train(data_path=data_path, output_dir=output_dir)


if __name__ == "__main__":
    main()
