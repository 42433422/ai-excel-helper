"""
AI 产品解析路由

提供：
- POST /api/ai/parse-single  解析单条产品语句
- POST /api/ai/parse-products 解析多条产品语句
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from flasgger import swag_from
from flask import Blueprint, jsonify, request

from app.services import AIProductParser, get_ai_product_parser

logger = logging.getLogger(__name__)

ai_parse_bp = Blueprint("ai_parse", __name__, url_prefix="/api/ai")


def _get_parser() -> AIProductParser:
    """获取解析器单例（简单缓存即可，避免频繁创建）。"""
    # Flask 进程级缓存即可；不引入全局状态复杂度
    if not hasattr(_get_parser, "_instance"):
        setattr(_get_parser, "_instance", get_ai_product_parser())
    return getattr(_get_parser, "_instance")


@ai_parse_bp.route("/parse-single", methods=["POST"])
@swag_from(
    {
        "summary": "解析单条产品语句",
        "description": "从原始文本中解析出产品型号/名称、规格、数量和单位，并做必备字段校验。",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "待解析文本"},
                        "use_ai": {
                            "type": "boolean",
                            "description": "是否启用 AI 解析（当前实现会自动降级到规则解析）",
                        },
                        "fallback_to_rule": {
                            "type": "boolean",
                            "description": "AI 失败时是否降级到规则解析",
                        },
                    },
                    "required": ["text"],
                },
            }
        ],
        "responses": {
            "200": {
                "description": "成功解析或校验失败返回",
                "schema": {"type": "object"},
            }
        },
    }
)
def parse_single() -> Any:
    """解析单条产品语句。"""
    try:
        data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        text: str = data.get("text", "") or ""
        use_ai: bool = bool(data.get("use_ai", True))
        fallback_to_rule: bool = bool(data.get("fallback_to_rule", True))

        if not text.strip():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "text 不能为空",
                        "missing_fields": ["unit", "quantity", "specification", "product"],
                        "invalid_reason": "输入为空，无法解析",
                    }
                ),
                400,
            )

        parser = _get_parser()
        result = parser.parse_single(text, use_ai=use_ai, fallback_to_rule=fallback_to_rule)
        status = 200 if result.get("success") else 422
        return jsonify(result), status
    except Exception as e:
        logger.error("解析单条产品语句失败: %s", e, exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500


@ai_parse_bp.route("/parse-products", methods=["POST"])
@swag_from(
    {
        "summary": "批量解析产品语句",
        "description": "批量解析产品文本列表，返回标准化结果列表。",
        "parameters": [
            {
                "name": "body",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "texts": {"type": "array", "items": {"type": "string"}},
                        "use_ai": {"type": "boolean"},
                        "fallback_to_rule": {"type": "boolean"},
                    },
                    "required": ["texts"],
                },
            }
        ],
        "responses": {
            "200": {
                "description": "解析结果列表",
                "schema": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "items": {"type": "array"},
                    },
                },
            }
        },
    }
)
def parse_products() -> Any:
    """批量解析产品语句。"""
    try:
        data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        texts: List[str] = data.get("texts") or []
        use_ai: bool = bool(data.get("use_ai", True))
        fallback_to_rule: bool = bool(data.get("fallback_to_rule", True))

        if not isinstance(texts, list) or not texts:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "texts 必须为非空数组",
                    }
                ),
                400,
            )

        parser = _get_parser()
        items = parser.parse_batch(texts, use_ai=use_ai, fallback_to_rule=fallback_to_rule)
        return jsonify({"success": True, "items": items}), 200
    except Exception as e:
        logger.error("批量解析产品语句失败: %s", e, exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

