# AI分析模块
import json
import logging
import requests
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.model_name = self.config.get("model_name", "deepseek")
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "https://api.deepseek.com/v1")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 2000)

        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        return """你是一个专业的会计助手，专注于处理订单、发货单和财务报表。

你的主要职责包括：
1. 分析订单信息，提取关键数据（客户名称、产品、数量、金额等）
2. 识别订单中的问题或异常
3. 生成处理建议和自动化操作指令
4. 提供财务相关的分析和建议

请始终以JSON格式返回分析结果，格式如下：
{
    "summary": "订单概述",
    "detected_fields": {
        "purchase_unit": "客户名称",
        "contact_person": "联系人",
        "purchase_date": "日期",
        "order_number": "订单编号",
        "total_amount": 总金额
    },
    "issues": ["发现的问题列表"],
    "action_required": true/false,
    "actions": [
        {
            "action_type": "操作类型",
            "target": "操作目标",
            "parameters": {"参数": "值"},
            "description": "操作描述"
        }
    ],
    "confidence": 0.0-1.0
}

可执行的操作类型包括：
- create_shipment: 创建发货单
- update_inventory: 更新库存
- send_notification: 发送通知
- calculate_total: 计算总金额
- verify_data: 验证数据
- manual_review: 人工审核
"""

    def analyze(self, content: str, context: str = "general") -> Dict:
        """
        分析内容

        Args:
            content: 要分析的内容（OCR识别结果或其他文本）
            context: 上下文信息

        Returns:
            分析结果字典
        """
        if not content or not content.strip():
            return {
                "error": "内容为空",
                "action_required": False,
                "confidence": 0.0
            }

        try:
            # 构建用户消息
            user_message = f"""请分析以下内容（上下文：{context}）：

{content}

请提供详细的分析结果，包括：
1. 主要信息摘要
2. 检测到的字段和值
3. 任何发现的问题
4. 建议的操作（如果有）
5. 分析的可信度"""

            # 调用AI API
            response = self._call_ai_api(user_message)

            if response is None:
                # 使用备用分析方法
                return self._fallback_analysis(content)

            return response

        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return {
                "error": str(e),
                "action_required": False,
                "confidence": 0.0
            }

    def _call_ai_api(self, user_message: str) -> Optional[Dict]:
        """调用AI API"""
        if not self.api_key:
            logger.warning("未配置API密钥，使用备用分析")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name if self.model_name != "deepseek" else "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            else:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None

    def _fallback_analysis(self, content: str) -> Dict:
        """备用分析方法（当API不可用时）"""
        analysis = {
            "summary": "本地分析结果",
            "detected_fields": {},
            "issues": [],
            "action_required": False,
            "actions": [],
            "confidence": 0.6,
            "analysis_method": "rule-based"
        }

        import re

        # 提取字段
        patterns = {
            "purchase_unit": r'购货单位[：:]\s*(.+?)(?:\n|$)',
            "contact_person": r'联系人[：:]\s*(.+?)(?:\n|$)',
            "purchase_date": r'(\d{4}[年-]\d{1,2}[月-]\d{1,2}[日]?)',
            "order_number": r'订单[编号]?[：:]\s*(.+?)(?:\n|$)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                analysis["detected_fields"][field] = match.group(1).strip()

        # 检测问题
        if not analysis["detected_fields"]:
            analysis["issues"].append("未能提取到关键字段")

        if len(content) < 20:
            analysis["issues"].append("内容过短，可能识别不完整")

        # 决定是否需要操作
        if analysis["detected_fields"] and len(analysis["issues"]) < 2:
            analysis["action_required"] = True
            analysis["actions"].append({
                "action_type": "manual_review",
                "target": "user",
                "parameters": {},
                "description": "请确认提取的信息是否正确"
            })

        return analysis

    def generate_response(self, analysis_result: Dict, response_type: str = "confirmation") -> str:
        """生成回复文本"""
        if response_type == "confirmation":
            fields = analysis_result.get("detected_fields", {})
            return f"""已收到您的订单信息，请确认以下内容：

客户名称：{fields.get('purchase_unit', '未识别')}
联系人：{fields.get('contact_person', '未识别')}
日期：{fields.get('purchase_date', '未识别')}
订单编号：{fields.get('order_number', '未识别')}

请回复"确认"继续处理，或提供更正信息。"""

        elif response_type == "notification":
            return f"""订单处理通知：

您的订单已收到，正在处理中。
预计发货时间：{analysis_result.get('estimated_delivery', '1-2个工作日')}
订单状态：处理中

如有疑问，请联系客服。"""

        elif response_type == "error":
            issues = analysis_result.get("issues", [])
            return f"""处理订单时遇到以下问题：

{chr(10).join(f'- {issue}' for issue in issues)}

请提供更多信息或更正后重新提交。"""

        return "感谢您的提交，我们会尽快处理。"

    def extract_order_info(self, content: str) -> Dict:
        """专门提取订单信息"""
        result = {
            "is_order": False,
            "order_info": {},
            "products": [],
            "totals": {}
        }

        import re

        # 检测是否为订单
        order_keywords = ["订单", "订购", "发货单", "购货", "购买"]
        if not any(kw in content for kw in order_keywords):
            return result

        result["is_order"] = True

        # 提取基本信息
        patterns = {
            "customer": r'购货单位[：:]\s*(.+?)(?:\n|$)',
            "contact": r'联系人[：:]\s*(.+?)(?:\n|$)',
            "phone": r'联系电话[：:]\s*([\d\-\+]+)',
            "date": r'(\d{4}[年-]\d{1,2}[月-]\d{1,2}[日]?)',
            "order_id": r'订单[编号]?[：:]\s*(.+?)(?:\n|$)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                result["order_info"][field] = match.group(1).strip()

        # 提取产品信息
        product_pattern = r'([A-Za-z0-9]+)\s+(.+?)\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)'
        for match in re.finditer(product_pattern, content):
            result["products"].append({
                "model": match.group(1),
                "name": match.group(2),
                "quantity": int(match.group(3)),
                "unit_price": float(match.group(4)),
                "total_price": float(match.group(5))
            })

        # 计算总金额
        total_pattern = r'合计[：:]\s*([\d\.]+)'
        total_match = re.search(total_pattern, content)
        if total_match:
            result["totals"]["declared_total"] = float(total_match.group(1))

        # 计算实际总金额
        if result["products"]:
            calculated_total = sum(p["total_price"] for p in result["products"])
            result["totals"]["calculated_total"] = calculated_total
            if result["totals"].get("declared_total"):
                if abs(result["totals"]["declared_total"] - calculated_total) > 0.01:
                    result["totals"]["discrepancy"] = result["totals"]["declared_total"] - calculated_total

        return result

    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_configured": bool(self.api_key)
        }


class ResponseGenerator:
    """回复生成器"""

    def __init__(self):
        self.templates = {
            "order_received": """
收到您的订单，感谢您的采购！

订单详情：
- 客户：{customer}
- 联系人：{contact}
- 日期：{date}
- 订单号：{order_id}

产品列表：
{product_list}

总金额：{total}元

我们正在处理您的订单，预计1-2个工作日内发货。
            """,

            "order_confirmed": """
您的订单已确认！

订单号：{order_id}
预计发货日期：{shipping_date}
物流信息：稍后更新

如有任何问题，请随时联系我们。
            """,

            "missing_info": """
您的订单信息不完整，请提供以下信息：

{missing_fields}

请补充后重新发送，感谢您的配合！
            """,

            "error": """
处理您的订单时遇到以下问题：

{error_message}

请检查后重新提交，或直接联系我们的人工客服。
            """
        }

    def generate(self, template_name: str, **kwargs) -> str:
        """生成回复"""
        template = self.templates.get(template_name, "感谢您的提交。")
        return template.format(**kwargs)

    def generate_product_list(self, products: List[Dict]) -> str:
        """生成产品列表文本"""
        lines = []
        for i, product in enumerate(products, 1):
            lines.append(f"{i}. {product['model']} {product['name']} ×{product['quantity']} = ¥{product['total_price']}")
        return '\n'.join(lines)

    def format_order_confirmation(self, order_info: Dict) -> str:
        """格式化订单确认信息"""
        customer = order_info.get("order_info", {}).get("customer", "未知客户")
        contact = order_info.get("order_info", {}).get("contact", "未知联系人")
        date = order_info.get("order_info", {}).get("date", datetime.now().strftime("%Y-%m-%d"))
        order_id = order_info.get("order_info", {}).get("order_id", "待分配")

        product_list = self.generate_product_list(order_info.get("products", []))
        total = order_info.get("totals", {}).get("calculated_total", 0)

        return self.generate(
            "order_received",
            customer=customer,
            contact=contact,
            date=date,
            order_id=order_id,
            product_list=product_list,
            total=total
        )
