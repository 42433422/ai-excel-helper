"""
AI 产品解析服务

当前实现采用规则 + 统一必填校验的混合方案：
- 先做槽位抽取（单位/数量/规格/产品）
- 再做统一字段完整性校验
- 预留 AI 接口，失败可降级到规则解析
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIProductParser:
    """AI/规则混合产品解析器。"""

    UNIT_PATTERN = re.compile(r"(桶|件|套|kg|KG|公斤|斤|箱|包|组)")
    QUANTITY_WITH_UNIT_PATTERN = re.compile(
        r"(?:要|需|数量|共|拿)?\s*(\d+(?:\.\d+)?)\s*(桶|件|套|kg|KG|公斤|斤|箱|包|组)"
    )
    SPEC_PATTERN = re.compile(
        r"((?:规格\s*\d+(?:\.\d+)?)|(?:\d+(?:\.\d+)?\s*(?:kg|KG|公斤)(?:/\s*(?:桶|件|套|箱|包|组))?))"
    )
    PRODUCT_CODE_PATTERN = re.compile(r"\b([A-Za-z]*\d{3,}[A-Za-z0-9-]*)\b")

    NOISE_TERMS = ("发货单", "送货单", "要", "需", "数量", "规格")

    def parse_single(
        self,
        raw_text: str,
        use_ai: bool = True,
        fallback_to_rule: bool = True,
    ) -> Dict[str, Any]:
        """解析单条产品语句。"""
        text = (raw_text or "").strip()
        if not text:
            return self._build_invalid_result(
                raw_text=raw_text,
                parse_method="rule",
                missing_fields=["unit", "quantity", "specification", "product"],
                invalid_reason="输入为空，无法解析",
            )

        if use_ai:
            ai_result = self._call_ai_api(text)
            if ai_result is not None:
                validated = self._validate_required_fields(ai_result)
                if validated["valid"]:
                    return validated["data"]
                if not fallback_to_rule:
                    return self._build_invalid_result(
                        raw_text=text,
                        parse_method="ai",
                        missing_fields=validated["missing_fields"],
                        invalid_reason=validated["invalid_reason"],
                    )

        rule_result = self._rule_parse(text)
        validated = self._validate_required_fields(rule_result)
        if validated["valid"]:
            return validated["data"]

        parse_method = "hybrid" if use_ai and fallback_to_rule else "rule"
        return self._build_invalid_result(
            raw_text=text,
            parse_method=parse_method,
            missing_fields=validated["missing_fields"],
            invalid_reason=validated["invalid_reason"],
            partial_data=rule_result,
        )

    def parse_batch(
        self,
        raw_texts: List[str],
        use_ai: bool = True,
        fallback_to_rule: bool = True,
    ) -> List[Dict[str, Any]]:
        """批量解析。"""
        return [
            self.parse_single(text, use_ai=use_ai, fallback_to_rule=fallback_to_rule)
            for text in (raw_texts or [])
        ]

    def _extract_unit(self, text: str) -> str:
        """提取单位。"""
        qty_match = self.QUANTITY_WITH_UNIT_PATTERN.search(text)
        if qty_match:
            return qty_match.group(2)
        unit_match = self.UNIT_PATTERN.search(text)
        return unit_match.group(1) if unit_match else ""

    def _rule_parse(self, text: str) -> Dict[str, Any]:
        """
        规则解析（槽位抽取）。
        顺序无关：分别抽取 quantity/unit/spec/product，再组合。
        """
        quantity: Optional[float] = None
        unit = self._extract_unit(text)
        qty_match = self.QUANTITY_WITH_UNIT_PATTERN.search(text)
        if qty_match:
            quantity = float(qty_match.group(1))

        spec = ""
        spec_match = self.SPEC_PATTERN.search(text)
        if spec_match:
            spec = re.sub(r"\s+", "", spec_match.group(1))

        code = ""
        code_match = self.PRODUCT_CODE_PATTERN.search(text)
        if code_match:
            code = code_match.group(1)

        # 产品名称 / 购买单位抽取：去掉已识别槽位与噪声词
        name_text = text
        if qty_match:
            name_text = name_text.replace(qty_match.group(0), " ")
        if spec_match:
            name_text = name_text.replace(spec_match.group(0), " ")
        if code:
            name_text = re.sub(re.escape(code), " ", name_text, count=1)
        for term in self.NOISE_TERMS:
            name_text = name_text.replace(term, " ")
        name_text = re.sub(r"\s+", " ", name_text).strip()

        purchase_unit = ""
        product_name = ""
        if name_text and len(name_text) >= 2:
            # 简单规则：连续的中文前缀视为购买单位，其余作为产品名称
            m = re.match(r"([\u4e00-\u9fff]{2,})(.*)", name_text)
            if m:
                purchase_unit = m.group(1).strip()
                product_name = m.group(2).strip()
            else:
                product_name = name_text

        # 如果还没有识别出型号，但产品名称中包含纯数字片段（通常用于编码），则提取为 product_code
        if not code and product_name:
            num_match = re.search(r"\d{3,}", product_name)
            if num_match:
                code = num_match.group(0)
                # 从名称中剥离该数字编码
                product_name = re.sub(re.escape(code), " ", product_name)
                product_name = re.sub(r"\s+", " ", product_name).strip()

        if quantity is not None and quantity.is_integer():
            quantity = int(quantity)

        return {
            "product_code": code,
            "product_name": product_name,
            "specification": spec,
            "quantity": quantity,
            "unit": unit,
            "purchase_unit": purchase_unit,
            "raw_data": text,
            "confidence": 0.8,
            "parse_method": "rule",
        }

    def _validate_required_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """统一必备字段校验：单位+数量+规格+（型号或名称）。"""
        missing_fields: List[str] = []
        if not data.get("unit"):
            missing_fields.append("unit")
        if data.get("quantity") in (None, ""):
            missing_fields.append("quantity")
        if not data.get("specification"):
            missing_fields.append("specification")
        if not (data.get("product_code") or data.get("product_name")):
            missing_fields.append("product")

        if missing_fields:
            invalid_reason = f"缺少必备字段: {', '.join(missing_fields)}"
            return {
                "valid": False,
                "missing_fields": missing_fields,
                "invalid_reason": invalid_reason,
            }

        normalized = dict(data)
        normalized["success"] = True
        normalized["missing_fields"] = []
        normalized["invalid_reason"] = ""
        return {"valid": True, "data": normalized}

    def _build_invalid_result(
        self,
        raw_text: str,
        parse_method: str,
        missing_fields: List[str],
        invalid_reason: str,
        partial_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base = {
            "success": False,
            "product_code": "",
            "product_name": "",
            "specification": "",
            "quantity": None,
            "unit": "",
            "raw_data": raw_text,
            "confidence": 0.0,
            "parse_method": parse_method,
            "missing_fields": missing_fields,
            "invalid_reason": invalid_reason,
        }
        if partial_data:
            base.update({k: v for k, v in partial_data.items() if k in base})
            base["success"] = False
            base["parse_method"] = parse_method
            base["missing_fields"] = missing_fields
            base["invalid_reason"] = invalid_reason
        return base

    def _call_ai_api(self, text: str) -> Optional[Dict[str, Any]]:
        """
        调用 DeepSeek AI 接口解析产品信息。
        解析失败时返回 None，触发规则降级。
        """
        try:
            import asyncio
            import json

            import httpx

            from .deepseek_intent_service import get_deepseek_api_key

            api_key = get_deepseek_api_key()
            if not api_key:
                logger.debug("未配置 DeepSeek API Key，降级到规则解析")
                return None

            system_prompt = """你是一个产品信息抽取助手。从用户输入中提取以下字段：

- product_code: 产品编号/型号（如 9803、2025）
- product_name: 产品名称
- specification: 规格（如 "规格 20"、"20kg"）
- quantity: 数量（数字）
- unit: 单位（桶/件/套/kg/箱/包等）
- purchase_unit: 购买单位/客户名称

要求：
1. 全部用中文回复
2. 只返回 JSON 格式，无需解释
3. quantity 必须是数字，不是中文
4. 如果某个字段无法提取，设为空字符串 ""
5. 只抽取明确提到信息，不要猜测

回复格式：
{"product_code": "", "product_name": "", "specification": "", "quantity": 0, "unit": "", "purchase_unit": ""}"""

            response_text = text.strip()

            async def call_api():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": response_text}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 200
                        }
                    )
                    result = resp.json()
                    if result.get("choices"):
                        return result["choices"][0]["message"]["content"]
                    return None

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    future = asyncio.ensure_future(call_api())
                    content = future.result(timeout=30.0)
                else:
                    content = asyncio.run(call_api())
            except RuntimeError:
                content = asyncio.run(call_api())

            if not content:
                return None

            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '{' in line:
                        content = '\n'.join(lines[i:])
                        break

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                quantity = data.get("quantity")
                if isinstance(quantity, str):
                    from .deepseek_intent_service import cn_to_number
                    quantity = cn_to_number(quantity)
                elif quantity is None:
                    quantity = None

                return {
                    "product_code": data.get("product_code", ""),
                    "product_name": data.get("product_name", ""),
                    "specification": data.get("specification", ""),
                    "quantity": quantity,
                    "unit": data.get("unit", ""),
                    "purchase_unit": data.get("purchase_unit", ""),
                    "raw_data": text,
                    "confidence": 0.9,
                    "parse_method": "ai",
                }

        except Exception as e:
            logger.error(f"AI 解析失败: {e}")

        return None
