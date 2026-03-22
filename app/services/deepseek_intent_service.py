# -*- coding: utf-8 -*-
"""
DeepSeek 意图识别服务 v2

支持意图组合识别：
- 主意图识别
- 槽位信息提取（单位、数量、规格、联系人等）
- 复合意图理解
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


class DeepSeekIntentRecognizer:
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

    async def recognize(self, message: str, context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """带槽位提取的意图识别（带缓存）"""
        cached = _intent_recognition_cache.get(message)
        if cached:
            logger.info(f"[INTENT_CACHE] 命中缓存: {message[:30]}... -> {cached.get('intent')}, slots={cached.get('slots')}")
            return cached

        logger.info(f"[INTENT_CACHE] 缓存未命中，需要调用 DeepSeek API")

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
                    result = response.json()
                    if result.get("choices"):
                        content = result["choices"][0]["message"]["content"]
                        parsed = self._parse_response(content, message)
                        _intent_recognition_cache.set(message, parsed)
                        return parsed
            except Exception as e:
                last_error = e
                logger.warning(f"DeepSeek 意图识别失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(0.5 * (attempt + 1))

        logger.error(f"DeepSeek 意图识别最终失败: {last_error}")
        fallback = self._fallback_result(message)
        _intent_recognition_cache.set(message, fallback)
        return fallback

    def _parse_response(self, content: str, original_message: str) -> Dict[str, Any]:
        import json

        content = content.strip()
        if content.startswith('```'):
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '{' in line:
                    content = '\n'.join(lines[i:])
                    break

        try:
            data = json.loads(content)
            intent = data.get("intent", "")
            confidence = float(data.get("confidence", 0.5))
            slots = data.get("slots", {})
            reasoning = data.get("reasoning", "")

            if intent in INTENT_DESCRIPTIONS or intent == "negation":
                normalized_slots = self._normalize_slots(slots, original_message)
                return {
                    "intent": intent,
                    "confidence": min(confidence, 1.0),
                    "slots": normalized_slots,
                    "reasoning": reasoning,
                    "source": "deepseek"
                }
        except json.JSONDecodeError:
            pass

        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                intent = data.get("intent", "")
                confidence = float(data.get("confidence", 0.5))
                slots = data.get("slots", {})
                reasoning = data.get("reasoning", "")

                if intent in INTENT_DESCRIPTIONS or intent == "negation":
                    normalized_slots = self._normalize_slots(slots, original_message)
                    return {
                        "intent": intent,
                        "confidence": min(confidence, 1.0),
                        "slots": normalized_slots,
                        "reasoning": reasoning,
                        "source": "deepseek"
                    }
        except (json.JSONDecodeError, ValueError):
            pass

        return self._fallback_result(original_message, content)

    def _normalize_slots(self, slots: Dict, message: str) -> Dict[str, Any]:
        """规范化槽位值"""
        normalized = {}

        for key, value in slots.items():
            if not value:
                continue

            value = str(value).strip()

            if key == "quantity_tins":
                match = re.search(r'(\d+|[一二两三四五六七八九十零]+)\s*桶', value) or re.search(r'(\d+|[一二两三四五六七八九十零]+)\s*桶', message)
                if match:
                    normalized[key] = self._cn_to_number(match.group(1))
                else:
                    try:
                        normalized[key] = int(re.search(r'\d+', value).group())
                    except:
                        normalized[key] = value

            elif key == "tin_spec":
                match = re.search(r'规格\s*(\d+)', message)
                if match:
                    normalized[key] = float(match.group(1))
                else:
                    try:
                        normalized[key] = float(re.search(r'\d+', value).group())
                    except:
                        normalized[key] = value

            elif key == "unit_name":
                match = re.search(r'给\s*([^\s，,。]+)|([^\s，,。]+)\s*(?:的|发货单)', message)
                if match:
                    normalized[key] = match.group(1) or match.group(2)
                else:
                    normalized[key] = value

            elif key in ("contact_person", "contact_phone", "contact_address"):
                normalized[key] = value

            else:
                normalized[key] = value

        return normalized

    def _cn_to_number(self, cn: str) -> int:
        """中文数字转整数"""
        cn_map = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        try:
            if cn in cn_map:
                return cn_map[cn]
            result = 0
            for char in cn:
                if char in cn_map:
                    result = result * 10 + cn_map[char]
            return result if result > 0 else int(cn)
        except:
            return int(re.search(r'\d+', cn).group()) if re.search(r'\d+', cn) else 0

    def _fallback_result(self, message: str, raw_response: str = "") -> Dict[str, Any]:
        return {
            "intent": None,
            "confidence": 0.0,
            "slots": {},
            "reasoning": "DeepSeek 识别失败",
            "source": "deepseek",
            "raw_response": raw_response
        }


class HybridIntentWithDeepSeek:
    """混合意图识别（规则 + DeepSeek/BERT + 槽位）"""

    def __init__(
        self,
        use_deepseek: bool = True,
        deepseek_api_key: Optional[str] = None,
        rule_priority: bool = True,
        confidence_threshold: float = 0.5,
        use_distilled: bool = False,
    ):
        self.use_deepseek = use_deepseek
        self.deepseek_api_key = deepseek_api_key
        self.rule_priority = rule_priority
        self.confidence_threshold = confidence_threshold
        self.deepseek_recognizer = None
        self.distilled_recognizer = None
        self.use_distilled = use_distilled

        if self.use_distilled:
            try:
                from .distilled_intent_service import get_distilled_recognizer
                self.distilled_recognizer = get_distilled_recognizer()
                if self.distilled_recognizer.is_available():
                    logger.info("使用蒸馏模型进行意图识别")
                else:
                    logger.warning("蒸馏模型不可用，切换到 DeepSeek")
                    self.use_distilled = False
            except Exception as e:
                logger.warning(f"无法加载蒸馏模型: {e}")
                self.use_distilled = False

        if self.use_deepseek and not self.use_distilled:
            self.deepseek_recognizer = DeepSeekIntentRecognizer(
                api_key=deepseek_api_key,
                confidence_threshold=confidence_threshold
            )

    async def recognize(self, message: str, context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        from .intent_service import recognize_intents as rule_recognize

        rule_result = rule_recognize(message)
        rule_result["sources_used"] = ["rule"]
        logger.info(f"[HYBRID] 规则识别结果: intent={rule_result.get('primary_intent')}, tool_key={rule_result.get('tool_key')}, is_greeting={rule_result.get('is_greeting')}, slots={rule_result.get('slots')}")

        if rule_result.get("is_greeting") or rule_result.get("is_goodbye") or rule_result.get("is_help"):
            rule_result["final_intent"] = rule_result.get("primary_intent") or rule_result.get("primary_intent")
            rule_result["intent_source"] = "rule"
            rule_result["slots"] = self._extract_slots_from_rule(message, rule_result)
            logger.info(f"[HYBRID] 简单意图，直接返回: {rule_result.get('primary_intent')}")
            return rule_result

        if rule_result.get("primary_intent") and rule_result.get("primary_intent") != "unk":
            rule_result["final_intent"] = rule_result["primary_intent"]
            rule_result["intent_source"] = "rule"
            rule_result["slots"] = self._extract_slots_from_rule(message, rule_result)
            logger.info(f"[HYBRID] 规则已命中，跳过 DeepSeek: {rule_result.get('primary_intent')}")
            return rule_result

        if not self.use_deepseek or not self.deepseek_recognizer:
            rule_result["final_intent"] = rule_result.get("primary_intent")
            rule_result["intent_source"] = "rule"
            rule_result["slots"] = self._extract_slots_from_rule(message, rule_result)
            return rule_result

        try:
            deepseek_result = await self.deepseek_recognizer.recognize(message, context)
            rule_result["deepseek_intent"] = deepseek_result.get("intent")
            rule_result["deepseek_confidence"] = deepseek_result.get("confidence", 0.0)
            rule_result["deepseek_slots"] = deepseek_result.get("slots", {})
            rule_result["deepseek_reasoning"] = deepseek_result.get("reasoning", "")
            rule_result["sources_used"].append("deepseek")

            if deepseek_result.get("confidence", 0.0) >= self.confidence_threshold:
                rule_result["final_intent"] = deepseek_result.get("intent")
                rule_result["tool_key"] = deepseek_result.get("intent")
                rule_result["intent_source"] = "deepseek"
                rule_result["intent_confidence"] = deepseek_result.get("confidence", 0.0)
                rule_result["slots"] = deepseek_result.get("slots", {})
            else:
                rule_result["final_intent"] = deepseek_result.get("intent")
                rule_result["tool_key"] = deepseek_result.get("intent")
                rule_result["intent_source"] = "deepseek_low_confidence"
                rule_result["intent_confidence"] = deepseek_result.get("confidence", 0.0)
                rule_result["slots"] = deepseek_result.get("slots", {})

        except Exception as e:
            logger.error(f"DeepSeek 意图识别失败: {e}")
            rule_result["final_intent"] = rule_result.get("primary_intent")
            rule_result["intent_source"] = "rule"
            rule_result["slots"] = self._extract_slots_from_rule(message, rule_result)

        return rule_result

    def _extract_slots_from_rule(self, message: str, rule_result: Dict) -> Dict[str, Any]:
        """从规则匹配结果中提取槽位"""
        slots = {}
        import re

        invalid_unit_names = {'生成', '发货', '发货单', '开单', '打单', '单', '给', '的', '我', '你', '他', '她', '它', '请', '问'}

        if '给' in message:
            idx = message.index('给')
            after_give = message[idx+1:].strip()
            if after_give:
                parts = re.split(r'[，,。\s]', after_give)
                if parts:
                    unit = parts[0].strip()
                    if unit and len(unit) > 1 and unit not in invalid_unit_names:
                        slots["unit_name"] = unit
        elif '帮' in message:
            idx = message.index('帮')
            after_help = message[idx+1:].strip()
            if after_help:
                unit_match = re.search(r'打([^\s，,。]+?)(?:的|货)', after_help)
                if unit_match:
                    unit = unit_match.group(1)
                    if unit and len(unit) > 1 and unit not in invalid_unit_names:
                        slots["unit_name"] = unit
                else:
                    parts = re.split(r'[，,。\s]', after_help)
                    if parts:
                        unit = parts[0].strip().lstrip('打')
                        if unit and len(unit) > 1 and unit not in invalid_unit_names:
                            slots["unit_name"] = unit
        else:
            unit_match = re.search(r'([^\s，,。]+?)\s*(?:的|发货单)', message)
            if unit_match:
                unit = unit_match.group(1)
                if unit and len(unit) > 1 and unit not in invalid_unit_names:
                    slots["unit_name"] = unit

        if "unit_name" not in slots:
            ship_match = re.search(r'^发货单([^\s，,。]{2,})', message)
            if ship_match:
                unit = ship_match.group(1)
                if unit and unit not in invalid_unit_names:
                    slots["unit_name"] = unit

        if "unit_name" not in slots:
            ship_match = re.search(r'^送货单([^\s，,。]{2,})', message)
            if ship_match:
                unit = ship_match.group(1)
                if unit and unit not in invalid_unit_names:
                    slots["unit_name"] = unit

        if "unit_name" not in slots:
            ship_match = re.search(r'^出货单([^\s，,。]{2,})', message)
            if ship_match:
                unit = ship_match.group(1)
                if unit and unit not in invalid_unit_names:
                    slots["unit_name"] = unit

        qty_match = re.search(r'(\d+|[一二两三四五六七八九十零]+)\s*桶', message)
        if qty_match:
            cn_map = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
            qty_str = qty_match.group(1)
            if qty_str in cn_map:
                slots["quantity_tins"] = cn_map[qty_str]
            else:
                slots["quantity_tins"] = int(qty_str)

        spec_match = re.search(r'规格\s*(\d+)', message)
        if spec_match:
            slots["tin_spec"] = float(spec_match.group(1))

        product_model_pattern = r'(\d{4}[A-Z]?)\s*(?:规格\s*(\d+(?:\.\d+)?))?'
        product_matches = re.findall(product_model_pattern, message)
        if product_matches:
            products = []
            for model, spec in product_matches:
                product_info = {"model": model}
                if spec:
                    product_info["spec"] = float(spec)
                products.append(product_info)
            if len(products) == 1:
                slots["product_model"] = products[0]["model"]
                if "tin_spec" not in slots and "spec" in products[0]:
                    slots["tin_spec"] = products[0]["spec"]
            elif len(products) > 1:
                slots["products"] = products

        logger.info(f"[SLOT_EXTRACTION_START] slots={slots}")
        
        # 处理 DeepSeek 可能返回的 contact_person 作为 unit_name
        if "contact_person" in slots and "unit_name" not in slots:
            contact = slots.pop("contact_person")
            slots["unit_name"] = contact
            logger.info(f"[SLOT_EXTRACTION] converted contact_person to unit_name: {contact}")
        
        invalid_unit_patterns = ['帮我', '查询', '请问', '请帮', '什么', '哪个']
        if "unit_name" in slots:
            unit_name = slots["unit_name"]
            needs_fix = any(p in unit_name for p in invalid_unit_patterns) or len(unit_name) > 6
            logger.info(f"[SLOT_EXTRACTION] unit_name={unit_name}, needs_fix={needs_fix}")
            if needs_fix and "keyword" in slots:
                keyword = slots["keyword"]
                unit_match = re.search(r'([^\s 的]{2,6}) 的 (\d{4}[A-Z]?)', keyword)
                logger.info(f"[SLOT_EXTRACTION] keyword={keyword}, unit_match={unit_match}")
                if unit_match:
                    potential_unit = unit_match.group(1)
                    model = unit_match.group(2)
                    from app.infrastructure.lookups.purchase_unit_resolver import (
                        resolve_purchase_unit,
                    )
                    resolved = resolve_purchase_unit(potential_unit)
                    logger.info(f"[SLOT_EXTRACTION] resolved={resolved}")
                    if resolved:
                        slots["unit_name"] = resolved.unit_name
                        slots["model_number"] = model
                    else:
                        slots["unit_name"] = potential_unit
                        slots["model_number"] = model
            else:
                from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit
                resolved = resolve_purchase_unit(unit_name)
                logger.info(f"[SLOT_EXTRACTION] resolved unit_name={resolved}")
                if resolved:
                    slots["unit_name"] = resolved.unit_name

        if "keyword" in slots and "unit_name" not in slots:
            keyword = slots["keyword"]
            logger.info(f"[SLOT_EXTRACTION_KEYWORD] keyword={keyword}")
            unit_match = re.search(r'([^\s 的]{2,6}) 的 (\d{4}[A-Z]?)', keyword)
            logger.info(f"[SLOT_EXTRACTION_KEYWORD] unit_match={unit_match}")
            if unit_match:
                potential_unit = unit_match.group(1)
                model = unit_match.group(2)
                logger.info(f"[SLOT_EXTRACTION_KEYWORD] potential_unit={potential_unit}, model={model}")
                from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit
                resolved = resolve_purchase_unit(potential_unit)
                logger.info(f"[SLOT_EXTRACTION_KEYWORD] resolved={resolved}")
                if resolved:
                    slots["unit_name"] = resolved.unit_name
                    slots["model_number"] = model
                else:
                    slots["unit_name"] = potential_unit
                    slots["model_number"] = model

        if "keyword" in slots and "model_number" not in slots:
            keyword = slots["keyword"]
            model_match = re.search(r'(\d{4}[A-Z]?)$', keyword)
            if model_match:
                slots["model_number"] = model_match.group(1)

        logger.info(f"[SLOT_EXTRACTION_END] final_slots={slots}")
        return slots

    def recognize_sync(self, message: str) -> Dict[str, Any]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.run(self.recognize(message))
            else:
                return asyncio.run(self.recognize(message))
        except Exception as e:
            logger.error(f"混合意图识别失败: {e}")
            from .intent_service import recognize_intents
            rule_result = recognize_intents(message)
            rule_result["slots"] = self._extract_slots_from_rule(message, rule_result)
            return rule_result


_deepseek_recognizer: Optional[DeepSeekIntentRecognizer] = None
_hybrid_with_deepseek: Optional[HybridIntentWithDeepSeek] = None


def get_deepseek_intent_recognizer(api_key: Optional[str] = None, confidence_threshold: float = 0.5) -> DeepSeekIntentRecognizer:
    global _deepseek_recognizer
    if _deepseek_recognizer is None:
        _deepseek_recognizer = DeepSeekIntentRecognizer(api_key=api_key, confidence_threshold=confidence_threshold)
    return _deepseek_recognizer


def get_hybrid_intent_with_deepseek(
    use_deepseek: bool = True,
    rule_priority: bool = True,
    confidence_threshold: float = 0.6,
    reset: bool = False
) -> HybridIntentWithDeepSeek:
    global _hybrid_with_deepseek
    if _hybrid_with_deepseek is None or reset:
        _hybrid_with_deepseek = HybridIntentWithDeepSeek(
            use_deepseek=use_deepseek,
            rule_priority=rule_priority,
            confidence_threshold=confidence_threshold
        )
    return _hybrid_with_deepseek


def reset_deepseek_intent_services():
    global _deepseek_recognizer, _hybrid_with_deepseek
    _deepseek_recognizer = None
    _hybrid_with_deepseek = None


def get_deepseek_api_key() -> str:
    """获取 DeepSeek API Key，优先环境变量，其次配置文件"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        from app.utils.path_utils import get_resource_path
        config_path = get_resource_path("config", "deepseek_config.py")
        if config_path and os.path.exists(config_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("xcagi_deepseek_config", config_path)
            if spec and spec.loader:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                return getattr(config_module, "DEEPSEEK_API_KEY", "") or ""
    except Exception:
        pass
    return ""


def cn_to_number(cn: str) -> int:
    """中文数字转整数"""
    cn_map = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    try:
        if cn in cn_map:
            return cn_map[cn]
        result = 0
        for char in cn:
            if char in cn_map:
                result = result * 10 + cn_map[char]
        return result if result > 0 else int(cn)
    except:
        return int(re.search(r'\d+', cn).group()) if re.search(r'\d+', cn) else 0
