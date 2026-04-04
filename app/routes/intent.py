# -*- coding: utf-8 -*-
"""
意图识别路由

提供意图识别模型推理的 HTTP 接口。
"""

import logging
import os

from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)
intent_bp = Blueprint("intent", __name__, url_prefix="/api/intent")


def get_classifier():
    """获取 classifier 单例，支持从 app.config 或环境变量获取 model_path"""
    # 须使用 bert_intent_service：含 is_available()、predict(..., return_probs=)。
    # app.services 包导出的 ai_engines.BertIntentClassifier 为精简版，会导致 /api/intent/health 500。
    from app.services.bert_intent_service import BertIntentClassifier

    model_path = current_app.config.get("INTENT_MODEL_PATH")
    if model_path:
        classifier = BertIntentClassifier(model_path=model_path)
    else:
        classifier = BertIntentClassifier()

    return classifier


@intent_bp.route("/health", methods=["GET"])
def health():
    """健康检查"""
    try:
        classifier = get_classifier()
        return jsonify({
            "status": "ok",
            "model_available": classifier.is_available()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "model_available": False,
            "error": str(e)
        }), 500


@intent_bp.route("/predict", methods=["POST"])
def predict():
    """单条文本意图预测"""
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        classifier = get_classifier()
        result = classifier.predict(text, return_probs=True)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({"error": str(e)}), 500


@intent_bp.route("/predict_batch", methods=["POST"])
def predict_batch():
    """批量文本意图预测"""
    data = request.get_json()
    texts = data.get("texts", [])
    if not texts:
        return jsonify({"error": "texts is required"}), 400
    try:
        classifier = get_classifier()
        results = classifier.predict_batch(texts, return_probs=True)
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        return jsonify({"error": str(e)}), 500