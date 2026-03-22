# -*- coding: utf-8 -*-
"""
意图识别模型训练入口脚本

支持训练和评估基于预训练模型的意图分类器

使用方法:
    # 训练模型
    python -m app.services.train_intent --mode train --data rasa/data/nlu.yml --model bert-base-chinese

    # 评估模型
    python -m app.services.train_intent --mode evaluate --model models/intent_bert/final

    # 批量测试
    python -m app.services.train_intent --mode test --model models/intent_bert/final --texts "生成发货单|查看客户列表"
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import torch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def train_model(
    data_path: str,
    model_name: str = "bert-base-chinese",
    output_dir: str = "models/intent_bert",
    epochs: int = 10,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_length: int = 64,
    export_onnx: bool = False,
):
    """训练意图识别模型"""
    try:
        from app.services.intent_trainer import (
            INTENT_LABELS,
            export_to_onnx,
            train_intent_model,
        )
    except ImportError as e:
        logger.error(f"无法导入训练模块: {e}")
        logger.info("请先安装依赖: pip install torch transformers sklearn pandas")
        return None

    logger.info("=" * 60)
    logger.info("意图识别模型训练")
    logger.info("=" * 60)
    logger.info(f"  数据路径: {data_path}")
    logger.info(f"  模型: {model_name}")
    logger.info(f"  输出目录: {output_dir}")
    logger.info(f"  训练轮数: {epochs}")
    logger.info(f"  批次大小: {batch_size}")
    logger.info(f"  学习率: {learning_rate}")
    logger.info(f"  设备: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    logger.info("=" * 60)

    try:
        model_path = train_intent_model(
            data_path=data_path,
            model_name=model_name,
            output_dir=output_dir,
            num_epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            max_length=max_length,
        )

        if export_onnx:
            onnx_path = str(Path(output_dir) / "model.onnx")
            export_to_onnx(str(model_path), onnx_path, max_length)

        logger.info("=" * 60)
        logger.info("训练完成!")
        logger.info(f"模型保存在: {model_path}")
        logger.info("=" * 60)
        return str(model_path)

    except Exception as e:
        logger.error(f"训练失败: {e}", exc_info=True)
        return None


def evaluate_model(model_path: str, data_path: Optional[str] = None):
    """评估模型"""
    try:
        from app.services.bert_intent_service import (
            INTENT_LABELS,
            BertIntentClassifier,
            get_bert_intent_service,
        )
    except ImportError as e:
        logger.error(f"无法导入推理模块: {e}")
        return

    logger.info("=" * 60)
    logger.info("模型评估")
    logger.info("=" * 60)

    classifier = BertIntentClassifier(model_path=model_path)

    if not classifier.is_available():
        logger.error("模型加载失败")
        return

    test_samples = [
        ("生成发货单", "shipment_generate"),
        ("查看客户列表", "customers"),
        ("产品有哪些", "products"),
        ("发货记录查询", "shipments"),
        ("发微信给客户", "wechat_send"),
        ("打印标签", "print_label"),
        ("上传Excel", "upload_file"),
        ("原材料库存", "materials"),
        ("发货单模板", "shipment_template"),
        ("分解Excel", "excel_decompose"),
        ("你好", "greet"),
        ("再见", "goodbye"),
        ("帮帮我", "help"),
        ("不要生成", "negation"),
        ("导出客户", "customer_export"),
    ]

    correct = 0
    total = len(test_samples)

    for text, expected in test_samples:
        result = classifier.predict(text)
        predicted = result["intent"]
        confidence = result["confidence"]
        is_correct = predicted == expected
        if is_correct:
            correct += 1
        status = "✓" if is_correct else "✗"
        logger.info(f"  {status} '{text}' -> {predicted} (期望: {expected}, 置信度: {confidence:.4f})")

    accuracy = correct / total * 100
    logger.info("=" * 60)
    logger.info(f"准确率: {accuracy:.2f}% ({correct}/{total})")
    logger.info("=" * 60)


def test_model(model_path: str, texts: List[str]):
    """测试模型"""
    try:
        from app.services.bert_intent_service import BertIntentClassifier
    except ImportError as e:
        logger.error(f"无法导入推理模块: {e}")
        return

    logger.info("=" * 60)
    logger.info("模型测试")
    logger.info("=" * 60)

    classifier = BertIntentClassifier(model_path=model_path)

    if not classifier.is_available():
        logger.warning("模型不可用，使用虚拟预测")

    for text in texts:
        result = classifier.predict(text, return_probs=True)
        logger.info(f"\n文本: {text}")
        logger.info(f"  意图: {result['intent']}")
        logger.info(f"  置信度: {result['confidence']:.4f}")
        if "all_probs" in result and result["all_probs"]:
            top3 = sorted(result["all_probs"].items(), key=lambda x: x[1], reverse=True)[:3]
            logger.info(f"  Top-3: {', '.join([f'{k}: {v:.4f}' for k, v in top3])}")

    logger.info("=" * 60)


def serve_model(model_path: str, port: int = 5000):
    """启动模型服务（使用 Blueprint 模式）"""
    try:
        import threading

        from flask import Flask

        app = Flask(__name__)

        app.config["INTENT_MODEL_PATH"] = model_path

        from app.routes.intent import intent_bp
        app.register_blueprint(intent_bp)

        logger.info(f"启动模型服务在 http://0.0.0.0:{port}")
        logger.info(f"意图识别 API: http://0.0.0.0:{port}/api/intent/predict")
        app.run(host="0.0.0.0", port=port, debug=False)

    except ImportError as e:
        logger.error(f"无法启动服务: {e}")
        logger.info("请确保 Flask 已安装: pip install flask")


def main():
    parser = argparse.ArgumentParser(description="意图识别模型训练和评估")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["train", "evaluate", "test", "serve"],
        default="train",
        help="运行模式",
    )
    parser.add_argument("--data", type=str, help="训练数据路径")
    parser.add_argument("--model", type=str, default="models/intent_bert/final", help="模型路径或名称")
    parser.add_argument("--output", type=str, default="models/intent_bert", help="输出目录")
    parser.add_argument("--epochs", type=int, default=10, help="训练轮数")
    parser.add_argument("--batch_size", type=int, default=16, help="批次大小")
    parser.add_argument("--lr", type=float, default=2e-5, help="学习率")
    parser.add_argument("--max_length", type=int, default=64, help="最大序列长度")
    parser.add_argument("--texts", type=str, help="测试文本，用 | 分隔")
    parser.add_argument("--port", type=int, default=5000, help="服务端口")
    parser.add_argument("--export_onnx", action="store_true", help="导出 ONNX 模型")

    args = parser.parse_args()

    if args.mode == "train":
        if not args.data:
            logger.error("训练模式需要指定 --data 参数")
            return
        train_model(
            data_path=args.data,
            model_name=args.model,
            output_dir=args.output,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            max_length=args.max_length,
            export_onnx=args.export_onnx,
        )

    elif args.mode == "evaluate":
        evaluate_model(model_path=args.model, data_path=args.data)

    elif args.mode == "test":
        texts = args.texts.split("|") if args.texts else ["生成发货单", "查看客户"]
        test_model(model_path=args.model, texts=texts)

    elif args.mode == "serve":
        serve_model(model_path=args.model, port=args.port)


if __name__ == "__main__":
    main()
