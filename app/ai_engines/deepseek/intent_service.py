# -*- coding: utf-8 -*-
"""
DeepSeek 意图识别服务 v2

支持意图组合识别：
- 主意图识别
- 槽位信息提取（单位、数量、规格、联系人等）
- 复合意图理解

原始模块位于 app/services/deepseek_intent_service.py
"""

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx

from app.utils.cache_manager import get_intent_deepseek_cache

logger = logging.getLogger(__name__)


class _IntentRecognitionCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, message: str) -> str:
        return hashlib.md5(message.strip().lower().encode()).hexdigest()

    def get(self, message: str) -> Optional[Dict[str, Any]]:
        key = self._make_key(message)
        if key not in self._cache:
            return None
        if time.time() - self._timestamps.get(key, 0) > self._ttl:
            del self._cache[key]
            del self._timestamps[key]
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, message: str, result: Dict[str, Any]) -> None:
        key = self._make_key(message)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
        self._cache[key] = result
        self._timestamps[key] = time.time()

    def clear(self) -> None:
        self._cache.clear()
        self._timestamps.clear()


_intent_recognition_cache = get_intent_deepseek_cache()

INTENT_DESCRIPTIONS = {
    "shipment_generate": "生成发货单、开单、打单、做出货单",
    "customers": "查看客户列表、购买单位、客户管理",
    "products": "查看产品列表、产品规格、产品库",
    "shipments": "查看发货记录、订单列表、出货记录",
    "wechat_send": "发微信、发消息给客户",
    "print_label": "打印标签、标签导出、商标打印、商标",
    "upload_file": "上传文件、导入数据、解析Excel",
    "materials": "原材料库存、材料库查询",
    "shipment_template": "发货单模板、模板设置",
    "excel_decompose": "分解Excel、提取词条、表头提取",
    "show_images": "查看图片、产品图片",
    "show_videos": "查看视频",
    "greet": "问候、打招呼",
    "goodbye": "告别、再见",
    "help": "请求帮助、功能介绍",
    "negation": "否定指令、不要做某事",
    "customer_export": "导出客户列表、导出Excel",
    "customer_edit": "修改客户信息、修改设置",
    "customer_supplement": "补充客户信息、添加联系人",
}

SLOT_DEFINITIONS = {
    "unit_name": "购买单位、销售客户（如：七彩乐园、侯雪梅）",
    "model_number": "产品编号、型号（如：9803、2025）",
    "tin_spec": "产品规格、桶规格（如：28、20）",
    "quantity_tins": "产品数量、桶数（如：1桶、3桶、5桶）",
    "contact_person": "联系人姓名（如：向总、张经理）",
    "contact_phone": "联系电话、手机号",
    "contact_address": "联系地址",
    "order_no": "订单编号",
    "keyword": "搜索关键词",
}


class DeepseekIntentClassifier:
    def __init__(self, api_key: Optional[str] = None, confidence_threshold: float = 0.5, timeout: float = 30.0, max_retries: int = 3):
        self.api_key = api_key
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None

    def _get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            try:
                from app.utils.path_utils import get_resource_path
                config_path = get_resource_path("config", "deepseek_config.py")
                if config_path and os.path.exists(config_path):
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("xcagi_deepseek_config", config_path)
                    if spec and spec.loader:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        key = getattr(config_module, "DEEPSEEK_API_KEY", "") or ""
            except Exception:
                pass
        return key

    def load_model(self) -> bool:
        return True

    async def recognize(self, message: str, context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        cached = _intent_recognition_cache.get(message)
        if cached:
            return cached

        intent_list = "\n".join([f"- {k}: {v}" for k, v in INTENT_DESCRIPTIONS.items()])
        slot_list = "\n".join([f"- {k}: {v}" for k, v in SLOT_DEFINITIONS.items()])

        system_prompt = f"""你是一个业务助手意图分类器。根据用户消息，识别意图和提取关键信息。

可选意图：
{intent_list}

槽位定义：
{slot_list}

分析要求：
1. 识别主意图（intent）
2. 提取所有提到的槽位信息（slots）
3. 如果是否定指令（不要、别），intent为negation，slots为空
4. 数量词需要标注真实数值

回复格式（严格JSON）：
{{"intent": "意图ID", "confidence": 0.0-1.0, "slots": {{"槽位名": "槽位值", ...}}, "reasoning": "简短分析"}}"""

        user_message = message
        if context:
            history = "\n".join([f"{m['role']}: {m['content']}" for m in context[-3:]])
            user_message = f"对话历史：\n{history}\n\n当前消息：{message}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._get_api_key()}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 300
                        }
                    )
                    response.raise_for_status()
                    result_data = response.json()
                    content = result_data["choices"][0]["message"]["content"]

                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

                    import json
                    result = json.loads(content)
                    result["source"] = "deepseek"
                    _intent_recognition_cache.set(message, result)
                    return result

            except Exception as e:
                last_error = e
                logger.warning(f"DeepSeek API 调用失败（第 {attempt + 1} 次）：{e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        return {
            "intent": "unk",
            "confidence": 0.0,
            "slots": {},
            "reasoning": f"API 调用失败：{last_error}",
            "source": "deepseek"
        }

    def predict(self, text: str) -> Dict[str, Any]:
        return {
            "intent": "unk",
            "confidence": 0.0,
            "source": "deepseek"
        }


import asyncio
