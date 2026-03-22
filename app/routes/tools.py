"""
工具管理路由

提供工具列表、分类管理等 API。
"""

import logging

from flasgger import swag_from
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
tools_bp = Blueprint('tools', __name__)


def _parse_order_text(order_text: str) -> dict:
    """
    解析订单文本，提取单位名和产品信息
    
    支持的格式：
    - "发货单七彩乐园 1 桶 9803 规格 12"
    - "送货单公司名称 2 箱产品 A 规格 100"
    - 等
    
    Returns:
        {
            "success": True/False,
            "unit_name": "单位名称",
            "products": [
                {
                    "name": "产品名称",
                    "quantity_tins": 桶数，
                    "tin_spec": 每桶规格，
                    "model_number": "型号"
                }
            ],
            "message": "错误消息（如果有）"
        }
    """
    try:
        import re

        original_text = (order_text or "").strip()

        # 去掉开头/中间出现的"发货单"、"送货单"、"出货单"
        # 目的：让用户即使在句子中间说到发货单（如“帮我打印一下发货单。xxx”）也能被解析。
        text = original_text
        for prefix in ['发货单', '送货单', '出货单']:
            idx = text.find(prefix)
            if idx != -1:
                text = text[idx + len(prefix):]
                break

        # 轻量清洗：把常见中文标点当作分隔符
        text = (
            text.replace('。', ' ')
            .replace('，', ' ')
            .replace(',', ' ')
            .replace('、', ' ')
            .replace('：', ' ')
            .replace(':', ' ')
        )

        # 归一化粒子：允许“的规格 / 的型号 / 的桶”等 ASR 文本形式
        text = text.replace('的规格', '规格')
        slot_text = (
            original_text.replace('。', ' ')
            .replace('，', ' ')
            .replace(',', ' ')
            .replace('、', ' ')
            .replace('：', ' ')
            .replace(':', ' ')
            .replace('的规格', '规格')
        )
        
        if not text:
            return {
                "success": False,
                "message": "订单文本格式不正确，缺少内容"
            }

        def _parse_cn_number(token: str):
            """解析阿拉伯数字/常见中文数字（支持二十八、三十、十、三桶中的三）。"""
            import re
            t = (token or "").strip()
            if not t:
                return None
            if re.fullmatch(r"\d+(?:\.\d+)?", t):
                return float(t) if "." in t else int(t)

            m = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
            if t in m:
                return m[t]
            if t == "十":
                return 10
            if re.fullmatch(r"[一二两三四五六七八九]十", t):
                return m[t[0]] * 10
            if re.fullmatch(r"十[一二三四五六七八九]", t):
                return 10 + m[t[1]]
            if re.fullmatch(r"[一二两三四五六七八九]十[一二三四五六七八九]", t):
                return m[t[0]] * 10 + m[t[2]]
            return None

        def _cleanup_unit_name(raw: str) -> str:
            import re
            s = (raw or "").strip()
            # 去掉口语填充词/命令词，保留真实单位名
            s = re.sub(r"^(哎|嗯|啊|呃)[，,\s]*", "", s)
            s = re.sub(r"^(帮我|给我|请)?\s*打印(一下)?", "", s)
            s = re.sub(r"^(把|给)?", "", s)
            s = s.replace("发货单", "").replace("送货单", "").replace("出货单", "")
            for token in ["打印一下", "打印", "给我", "帮我", "一下", "哎", "嗯", "啊", "呃", "桶", "要", "来", "拿"]:
                s = s.replace(token, "")
            # 避免把型号数字残留到单位名中
            s = re.sub(r"\d{3,6}", "", s)
            s = re.sub(r"\s+", "", s)
            s = s.rstrip("的").strip()
            return s

        def _build_missing_prompt(unit_name=None, model_number=None, tin_spec=None, quantity_tins=None):
            missing = []
            if not unit_name:
                missing.append("单位")
            if not quantity_tins:
                missing.append("桶数")
            if not model_number:
                missing.append("编号/型号")
            if not tin_spec:
                missing.append("规格")
            if not missing:
                return None
            recognized = []
            if unit_name:
                recognized.append(f"单位 {unit_name}")
            if model_number:
                recognized.append(f"编号 {model_number}")
            if tin_spec:
                recognized.append(f"规格 {tin_spec}")
            recognized_text = ("（已识别：" + "，".join(recognized) + "）") if recognized else ""
            if missing == ["桶数"]:
                return f"还缺少桶数，请告诉我需要多少桶？{recognized_text}"
            if missing == ["单位"]:
                return f"还缺少单位名称，请补充购买单位。{recognized_text}"
            if missing == ["规格"]:
                return f"还缺少规格，请补充规格数值。{recognized_text}"
            if missing == ["编号/型号"]:
                return f"还缺少编号/型号，请补充。{recognized_text}"
            return f"还缺少{'、'.join(missing)}，请补充。{recognized_text}"

        # 槽位解析（任意语序口语）
        # 示例：给我打印七彩乐园发货单，编号9803，规格二十八，一共三桶
        # 先从全句提取 编号/规格/桶数，再从剩余文本抽单位名
        slot_model = None
        slot_spec = None
        slot_qty_tins = None

        m_model = re.search(r"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*(\d{3,6})", slot_text)
        if m_model:
            slot_model = m_model.group(1)
        else:
            # 兜底：取“规格”前最近的数字串作为型号（如 9803规格28）
            m_model2 = re.search(r"(\d{3,6})\s*(?:的)?\s*规格", slot_text)
            if m_model2:
                slot_model = m_model2.group(1)

        # 规格支持阿拉伯数字与中文数字，并兼容"规格12要3桶/规格二十八三桶"等连读口语
        if "规格" in slot_text:
            after_spec = slot_text.split("规格", 1)[1]
            number_token_pattern = r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])"
            qty_token_pattern = r"(?:\d+|[一二两三四五六七八九十零〇两]+)"

            # 优先匹配"规格XX(要|来|拿)?三桶"这类连读
            m_spec_qty = re.search(
                rf"^\s*[:：]?\s*({number_token_pattern})(?:\s*(?:要|来|拿|共|一共|总共)?\s*({qty_token_pattern})\s*桶)?",
                after_spec,
            )
            if m_spec_qty:
                spec_num = _parse_cn_number(m_spec_qty.group(1))
                if spec_num is not None:
                    slot_spec = float(spec_num)
                if m_spec_qty.group(2):
                    qty_num = _parse_cn_number(m_spec_qty.group(2))
                    if qty_num is not None:
                        slot_qty_tins = int(qty_num)
            else:
                # 兜底：只提取规格
                m_spec = re.search(r"^\s*[:：]?\s*(\d+(?:\.\d+)?)", after_spec)
                if m_spec:
                    spec_num = _parse_cn_number(m_spec.group(1))
                    if spec_num is not None:
                        slot_spec = float(spec_num)
                else:
                    m_spec_cn = re.search(r"^\s*[:：]?\s*([一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])", after_spec)
                    if m_spec_cn:
                        spec_num = _parse_cn_number(m_spec_cn.group(1))
                        if spec_num is not None:
                            slot_spec = float(spec_num)

        # 如果规格连读已经提取了桶数，就不再重复提取（支持“要3桶/来3桶/拿3桶”）
        if slot_qty_tins is None:
            m_qty = re.search(r"(?:一共|总共|共|要|来|拿)?\s*(\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)
            if m_qty:
                qty_num = _parse_cn_number(m_qty.group(1))
                if qty_num is not None:
                    slot_qty_tins = int(qty_num)
        # 单位名：移除命令词+关键槽位片段后取前半段
        unit_candidate = slot_text
        unit_candidate = re.sub(r"(发货单|送货单|出货单)", " ", unit_candidate)
        unit_candidate = re.sub(r"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*\d{3,6}", " ", unit_candidate)
        unit_candidate = re.sub(r"规格\s*[:：]?\s*(?:\d+(?:\.\d+)?|[一二两三四五六七八九十零〇两]+)(?:\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶)?", " ", unit_candidate)
        unit_candidate = re.sub(r"(?:一共|总共|共|要|来|拿)?\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶", " ", unit_candidate)
        unit_candidate = re.sub(r"\d{3,6}", " ", unit_candidate)
        unit_candidate = re.sub(r"[，,\s]+", " ", unit_candidate).strip()
        slot_unit = _cleanup_unit_name(unit_candidate)
        if not slot_unit:
            m_unit = re.search(r"(?:打印(?:一下)?)\s*([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text)
            if not m_unit:
                m_unit = re.search(r"([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text)
            if m_unit:
                slot_unit = _cleanup_unit_name(m_unit.group(1))
        if not slot_unit:
            m_unit3 = re.search(r"([^，,。0-9]+?)的(?:发货单|送货单|出货单)", slot_text)
            if m_unit3:
                slot_unit = _cleanup_unit_name(m_unit3.group(1))
        if not slot_unit:
            for bill_kw in ["发货单", "送货单", "出货单"]:
                if bill_kw in slot_text:
                    slot_unit = _cleanup_unit_name(slot_text.split(bill_kw)[0])
                    if slot_unit:
                        break
        if not slot_unit:
            # 最后兜底：提取“打印一下XX发货单”中 XX
            m_unit4 = re.search(r"打印(?:一下)?\s*([^，,。]+?)\s*(?:发货单|送货单|出货单)", slot_text)
            if m_unit4:
                slot_unit = _cleanup_unit_name(m_unit4.group(1))

        # 仅在口语槽位信号较强时才走该分支，避免覆盖原有“1桶酒吧零三规格28”成功路径
        slot_mode_trigger = (
            ("编号" in slot_text or "型号" in slot_text or "一共" in slot_text or "总共" in slot_text or "共" in slot_text)
            or re.search(r"\d{3,6}\s*(?:的)?\s*规格", slot_text)
            or re.search(r"(?:要|来|拿)\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)
        )
        if slot_mode_trigger and (slot_model or slot_spec or slot_qty_tins):
            # 缺项追问（不中断工作流）
            missing_prompt = _build_missing_prompt(
                unit_name=slot_unit,
                model_number=slot_model,
                tin_spec=int(slot_spec) if isinstance(slot_spec, float) and slot_spec.is_integer() else slot_spec,
                quantity_tins=slot_qty_tins,
            )
            if missing_prompt:
                return {"success": False, "message": missing_prompt}

            # 完整则直接返回，避免后续固定顺序正则再失败
            return {
                "success": True,
                "unit_name": slot_unit,
                "products": [{
                    "name": "",
                    "model_number": str(slot_model),
                    "quantity_tins": int(slot_qty_tins),
                    "tin_spec": float(slot_spec),
                }]
            }
        
        # -----------------------------
        # 归一化解析用的小工具
        # -----------------------------
        CHINESE_DIGIT_MAP = {
            "零": "0", "〇": "0",
            "一": "1",
            "二": "2",
            "三": "3",
            "四": "4",
            "五": "5",
            "六": "6",
            "七": "7",
            "八": "8",
            "九": "9",
            "两": "2",
        }

        # ASR 误读片段到数字片段的“分段纠错映射”
        # 例如：酒吧零三 -> (酒吧->98) + (零三->03) -> 9803
        ASR_MODEL_SEGMENT_MAP = {
            "酒吧": "98",
        }

        def _normalize_trailing_unit_name(name: str) -> str:
            # 例如：七彩乐园的 -> 七彩乐园
            return (name or "").strip().rstrip("的").strip()

        def _normalize_chinese_digits(token: str) -> str:
            """
            把“零三/一/两”等这种“逐位数字串”转成阿拉伯数字串，保留前导零（如 零三 -> 03）。
            """
            token = (token or "").strip()
            if not token:
                return ""

            # 纯阿拉伯数字：直接返回
            if re.fullmatch(r"\d+(?:\.\d+)?", token):
                return token

            # 仅由中文数字字符组成（逐位映射）
            if all(ch in CHINESE_DIGIT_MAP for ch in token):
                return "".join(CHINESE_DIGIT_MAP[ch] for ch in token)

            # 兜底：在 token 内提取中文数字字符并逐位映射
            digits = []
            for ch in token:
                if ch in CHINESE_DIGIT_MAP:
                    digits.append(CHINESE_DIGIT_MAP[ch])
            return "".join(digits)

        def _normalize_quantity_token(quantity_token: str):
            """
            把数量（如“一”）归一为整数桶数。
            """
            quantity_token = (quantity_token or "").strip()
            if not quantity_token:
                return None
            if re.fullmatch(r"\d+", quantity_token):
                return int(quantity_token)
            digits = _normalize_chinese_digits(quantity_token)
            if digits.isdigit():
                return int(digits)
            return None

        def _normalize_model_number_token(model_token: str) -> str:
            """
            把型号 token 归一为阿拉伯数字字符串。
            - 支持 ASR 误读分段（如 酒吧->98）
            - 支持中文数字逐位映射（零三->03）
            """
            token = (model_token or "").strip()
            if not token:
                return ""

            # 直接是阿拉伯数字
            if re.fullmatch(r"\d+", token):
                return token

            # 逐段纠错：把已知误读片段先替换为数字片段
            for k, v in ASR_MODEL_SEGMENT_MAP.items():
                if k in token:
                    token = token.replace(k, v)

            # 现在 token 可能形如：98零三
            # 提取阿拉伯数字段 + 中文数字段，并拼接
            parts: list[str] = []
            # 先把连续阿拉伯数字保留下来
            for m in re.finditer(r"\d+", token):
                parts.append(m.group(0))

            # 再把剩余中文数字字符逐位映射后拼接
            # 注意：我们不在此处保留分隔符，只做可控拼接
            chinese_digits = _normalize_chinese_digits("".join(ch for ch in token if ch in CHINESE_DIGIT_MAP))
            if chinese_digits:
                parts.append(chinese_digits)

            normalized = "".join(parts)
            # 兜底：如果没有 parts，尝试把 token 内所有中文数字直接映射
            if not normalized:
                normalized = _normalize_chinese_digits(token)
            return normalized

        # -----------------------------
        # 多产品解析：支持 "帮打蔺宇的货单，10桶5003-2737B规格25，4桶5003-2737A规格25"
        # -----------------------------
        text_for_multi = re.sub(r'[，,。\s]+', '', text)
        multi_pattern = r'(\d+)桶(\d+[A-Z]?(?:-\d+[A-Z]?)?)规格(\d+)(?=\d+桶|$)'
        multi_matches = list(re.finditer(multi_pattern, text_for_multi))
        if multi_matches and len(multi_matches) >= 1:
            products = []
            for m in multi_matches:
                qty = int(m.group(1))
                model = m.group(2)
                spec = int(m.group(3))
                products.append({"name": "", "model_number": model, "quantity_tins": qty, "tin_spec": float(spec)})
            if products:
                unit_candidate = None
                text_without_products = re.sub(r'\d+桶\d+[A-Z]?(?:-\d+[A-Z]?)规格\d+(?=\d+桶|$)', '', text_for_multi)
                m_unit = re.search(r'帮打(.+?)货单', text_without_products)
                if m_unit:
                    unit_candidate = _cleanup_unit_name(m_unit.group(1))
                else:
                    for prefix in ['的货单', '发货单', '送货单', '出货单', '货单']:
                        idx = text_without_products.find(prefix)
                        if idx >= 0:
                            text_before = text_without_products[:idx]
                            m2 = re.search(r'([^\d，,。]+?)$', text_before)
                            if m2:
                                unit_candidate = _cleanup_unit_name(m2.group(1))
                                break
                if not unit_candidate:
                    m2 = re.search(r'^([^\d，,。]+?)', text_without_products)
                    if m2:
                        unit_candidate = _cleanup_unit_name(m2.group(1))
                if unit_candidate and products:
                    return {
                        "success": True,
                        "unit_name": unit_candidate,
                        "products": products
                    }

        # -----------------------------
        # 简单解析：按"桶"、"规格"分割
        # -----------------------------
        patterns = [
            # 模式 1: "七彩乐园 1 桶 9803 规格 12"
            # 允许数量/型号为中文数字/ASR token，且允许“的规格”
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+?)\s*规格\s*(\d+(?:\.\d+)?)',
            # 模式 2: "七彩乐园 1 桶 9803"
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+)$',
            # 模式 3: "七彩乐园 2 箱产品 A"
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*(箱 | 件)\s*(.+)',
            # 模式 4: "公司 A 3 公斤材料 B"
            r'^([^\d]+?)(\d+(?:\.\d+)?|[一二三四五六七八九十零〇两]+)\s*(公斤|kg)\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    unit_name = _normalize_trailing_unit_name(groups[0])
                    
                    # 判断是否是数字开头（型号）还是单位
                    unit_or_measure = (groups[2] or "").strip()
                    if unit_or_measure in ['箱', '件', '公斤', 'kg']:
                        # 模式 3 或 4
                        try:
                            # 箱/件：尽量解析为整数；公斤/kg：允许小数（并支持中文数字）
                            if unit_or_measure in ['箱', '件']:
                                quantity = float(_normalize_quantity_token(groups[1]) or 0)
                            else:
                                token = (groups[1] or "").strip()
                                if re.fullmatch(r"\d+(?:\.\d+)?", token):
                                    quantity = float(token)
                                else:
                                    digits = _normalize_chinese_digits(token)
                                    quantity = float(digits) if digits else float(token)
                        except:
                            quantity = 1
                        
                        product_name = groups[3].strip() if len(groups) > 3 else "产品"
                        
                        result = {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": product_name,
                                "tin_spec": 10.0,  # 默认规格
                            }]
                        }
                        
                        if '公斤' in unit_or_measure or 'kg' in unit_or_measure:
                            result["products"][0]["quantity_kg"] = quantity
                        else:
                            result["products"][0]["quantity_tins"] = int(quantity) if unit_or_measure in ['箱', '件'] else quantity
                        
                        return result
                    else:
                        # 模式 1 或 2: "七彩乐园 1 桶 9803 规格 12"
                        try:
                            quantity = _normalize_quantity_token(groups[1])
                            if quantity is None:
                                return {
                                    "success": False,
                                    "message": "解析数字失败（数量无法识别）"
                                }

                            model_number = _normalize_model_number_token(groups[2])
                            if not model_number:
                                return {
                                    "success": False,
                                    "message": "解析数字失败（型号无法识别）"
                                }

                            spec = float(groups[3]) if len(groups) > 3 else 10.0
                        except:
                            return {
                                "success": False,
                                "message": "解析数字失败"
                            }
                        
                        # name 留空，让后续数据库匹配来填充正确的产品名称
                        return {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": "",  # 留空，等待数据库匹配
                                "model_number": model_number,
                                "quantity_tins": quantity,
                                "tin_spec": spec,
                            }]
                        }
        
        # 弱匹配：打印/报型号+规格，但缺少“桶/箱/件/公斤/kg”数量容器时
        # 例如：打印一下七彩乐园的9803规格28（用户只给了型号与规格，没有桶数）
        # 目标：让系统追问“需要多少桶？”，而不是忽略或走产品流程。
        has_container_qty = any(k in text for k in ["桶", "箱", "件", "公斤", "kg"])
        if not has_container_qty:
            m = re.search(r'([^\d]+?)\s*(\d+)\s*规格\s*(\d+(?:\.\d+)?)', text)
            if m:
                unit_part = m.group(1)
                model_token = m.group(2)
                spec_token = m.group(3)

                unit_name = _normalize_trailing_unit_name(unit_part)
                # 去掉可能出现在 unit_part 前缀的口语/指令词（如“打印一下七彩乐园的”）
                unit_name = re.sub(r'^(帮我|给我)?打印(一下)?|^打单|^开单', '', unit_name).strip()
                model_number = _normalize_model_number_token(model_token)
                tin_spec = float(spec_token)

                if unit_name and model_number and tin_spec is not None:
                    spec_display = int(tin_spec) if tin_spec.is_integer() else tin_spec
                    return {
                        "success": False,
                        "message": f"还缺少桶数（数量）。已识别：{unit_name} / {model_number} / 规格 {spec_display}。请告诉我需要多少桶？"
                    }

        # AI 结构化抽取兜底：规则仍失败时尝试从口语中抽取 unit/model/spec/qty
        try:
            import json
            import os

            import httpx

            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if api_key:
                prompt = (
                    "请从下面中文订单口语中抽取 JSON 字段："
                    "unit_name, model_number, tin_spec, quantity_tins。"
                    "仅返回 JSON，不要解释，不要 markdown。\n"
                    f"文本：{text}"
                )
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": "你是结构化信息抽取助手，只输出 JSON。"},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.0,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = (
                            (data.get("choices") or [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                        # 兼容 ```json ... ``` 包裹
                        content = re.sub(r"^```json\s*|^```\s*|```$", "", content).strip()
                        parsed = json.loads(content) if content else {}
                        ai_unit = _cleanup_unit_name(str(parsed.get("unit_name", "")).strip())
                        ai_model = str(parsed.get("model_number", "")).strip()
                        ai_spec_raw = str(parsed.get("tin_spec", "")).strip()
                        ai_qty_raw = str(parsed.get("quantity_tins", "")).strip()
                        ai_spec = _parse_cn_number(ai_spec_raw) if ai_spec_raw else None
                        ai_qty = _parse_cn_number(ai_qty_raw) if ai_qty_raw else None

                        missing_prompt = _build_missing_prompt(
                            unit_name=ai_unit,
                            model_number=ai_model or None,
                            tin_spec=ai_spec,
                            quantity_tins=int(ai_qty) if ai_qty else None,
                        )
                        if missing_prompt:
                            return {"success": False, "message": missing_prompt}

                        if ai_unit and ai_model and ai_spec and ai_qty:
                            return {
                                "success": True,
                                "unit_name": ai_unit,
                                "products": [{
                                    "name": "",
                                    "model_number": ai_model,
                                    "quantity_tins": int(ai_qty),
                                    "tin_spec": float(ai_spec),
                                }],
                            }
        except Exception as ai_err:
            logger.warning(f"AI 结构化抽取兜底失败，回退规则流程: {ai_err}")

        # 如果所有模式都不匹配，尝试简单分割
        parts = text.split()
        if len(parts) >= 2:
            unit_name = parts[0].strip()
            return {
                "success": True,
                "unit_name": unit_name,
                "products": [{
                    "name": " ".join(parts[1:]),
                    "quantity_tins": 1,
                    "tin_spec": 10.0,
                }]
            }
        
        return {
            "success": False,
            "message": f"无法解析订单文本：{order_text}，请使用格式：发货单 + 单位名 + 数量 + 桶 + 型号 + 规格"
        }
        
    except Exception as e:
        logger.error(f"解析订单文本失败：{e}")
        return {
            "success": False,
            "message": f"解析失败：{str(e)}"
        }


@tools_bp.route('/api/database/backup', methods=['POST'])
@swag_from({
    'summary': '备份数据库',
    'description': '备份 SQLite 数据库到备份目录',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'file_path': {'type': 'string', 'description': '备份文件路径'},
                    'filename': {'type': 'string', 'description': '备份文件名'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def backup_database():
    """备份数据库"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.backup_database()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"备份数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/restore', methods=['POST'])
@swag_from({
    'summary': '恢复数据库',
    'description': '从备份文件恢复数据库',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['backup_file'],
                'properties': {
                    'backup_file': {'type': 'string', 'description': '备份文件路径或文件名'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def restore_database():
    """恢复数据库"""
    try:
        from app.services import get_database_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        backup_file = data.get('backup_file')
        if not backup_file:
            return jsonify({"success": False, "message": "缺少参数：backup_file"}), 400
        
        db_service = get_database_service()
        result = db_service.restore_database(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"恢复数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backups', methods=['GET'])
@swag_from({
    'summary': '列出备份文件',
    'description': '列出所有数据库备份文件',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'backups': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'filename': {'type': 'string'},
                                'file_path': {'type': 'string'},
                                'size': {'type': 'integer'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    },
                    'count': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def list_database_backups():
    """列出备份文件"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.list_backups()
        return jsonify(result)
    except Exception as e:
        logger.error(f"列出备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backup/<path:backup_file>', methods=['DELETE'])
@swag_from({
    'summary': '删除备份文件',
    'description': '删除指定的数据库备份文件',
    'parameters': [
        {
            'name': 'backup_file',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '备份文件名'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def delete_database_backup(backup_file):
    """删除备份文件"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.delete_backup(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"删除备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['GET'])
@swag_from({
    'summary': '获取开机自启配置',
    'description': '获取当前应用的开机自启状态',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                            'app_path': {'type': 'string'},
                            'startup_path': {'type': 'string'},
                            'platform': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_startup_config():
    """获取开机自启配置"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_startup_config()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取开机自启配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['POST'])
@swag_from({
    'summary': '启用开机自启',
    'description': '启用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'command': {'type': 'string', 'description': '启动命令'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def enable_startup():
    """启用开机自启"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.enable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"启用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['DELETE'])
@swag_from({
    'summary': '禁用开机自启',
    'description': '禁用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def disable_startup():
    """禁用开机自启"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.disable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"禁用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/info', methods=['GET'])
@swag_from({
    'summary': '获取系统信息',
    'description': '获取系统信息，包括操作系统、Python 版本等',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'platform': {'type': 'string'},
                            'platform_version': {'type': 'string'},
                            'python_version': {'type': 'string'},
                            'app_path': {'type': 'string'},
                            'working_directory': {'type': 'string'},
                            'executable': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_system_info():
    """获取系统信息"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_system_info()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取系统信息失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['GET'])
@swag_from({
    'summary': '获取打印机配置',
    'description': '获取可用的打印机列表和默认打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printers': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'default_printer': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_printer_config():
    """获取打印机配置"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_printer_config()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取打印机配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['POST'])
@swag_from({
    'summary': '设置默认打印机',
    'description': '设置系统默认打印机',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['printer_name'],
                'properties': {
                    'printer_name': {'type': 'string', 'description': '打印机名称'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def set_default_printer():
    """设置默认打印机"""
    try:
        from app.services import get_system_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        printer_name = data.get('printer_name')
        if not printer_name:
            return jsonify({"success": False, "message": "缺少参数：printer_name"}), 400
        
        system_service = get_system_service()
        result = system_service.set_default_printer(printer_name)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"设置默认打印机失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/db-tools', methods=['GET'])
def get_db_tools_compat():
    """兼容旧版前端的 /api/db-tools 接口"""
    return get_tools_list()


@tools_bp.route('/api/tools', methods=['GET'])
@swag_from({
    'summary': '获取工具列表',
    'description': '获取可用工具列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'tools': {'type': 'array'}
                }
            }
        }
    }
})
def get_tools_list():
    """获取可用工具列表"""
    try:
        tools = [
            {"id": "products", "name": "产品管理", "description": "查看、搜索产品与型号，管理产品库", "category": "products",
             "actions": [{"name": "查看产品", "description": "查看所有产品列表"}, {"name": "添加产品", "description": "添加新产品"}, {"name": "搜索产品", "description": "按型号或名称搜索"}]},
            {"id": "customers", "name": "客户/购买单位", "description": "查看、编辑客户列表，或上传 Excel 更新购买单位", "category": "customers",
             "actions": [{"name": "查看客户", "description": "查看客户/购买单位列表"}, {"name": "添加客户", "description": "添加新客户"}, {"name": "搜索客户", "description": "搜索客户"}]},
            {"id": "orders", "name": "出货单", "description": "查看出货订单、创建订单、导出 Excel", "category": "orders",
             "actions": [{"name": "查看订单", "description": "查看出货订单列表"}, {"name": "创建订单", "description": "创建新订单"}, {"name": "导出订单", "description": "导出订单到 Excel"}]},
            {"id": "shipment_generate", "name": "生成发货单", "description": "按订单文本或「打印+订单」生成发货单，支持编号模式与商标导出", "category": "orders",
             "actions": [{"name": "生成发货单", "description": "输入订单内容直接生成发货单"}]},
            {"id": "print", "name": "标签打印", "description": "打印产品标签或导出商标到本地下载", "category": "print",
             "actions": [{"name": "打印标签", "description": "打印商标导出目录下标签"}, {"name": "批量打印", "description": "批量打印多个标签"}, {"name": "查看标签", "description": "查看可用标签列表"}]},
            {"id": "materials", "name": "原材料仓库", "description": "查看原材料库存与预警", "category": "materials",
             "actions": [{"name": "查看库存", "description": "查看原材料库存"}, {"name": "预警设置", "description": "设置库存预警阈值"}]},
            {"id": "database", "name": "数据库管理", "description": "数据库备份与恢复", "category": "database",
             "actions": [{"name": "备份", "description": "备份数据库"}, {"name": "恢复", "description": "从备份恢复"}]},
            {"id": "system", "name": "系统设置", "description": "开机自启、打印配置等", "category": "system",
             "actions": [{"name": "开机启动", "description": "设置开机自启动"}, {"name": "打印设置", "description": "配置打印机"}]},
            {"id": "shipment_template", "name": "发货单模板", "description": "保存/展示模板、可编辑词条与字段映射、介绍抬头与金额计算", "category": "orders",
             "actions": [{"name": "保存模板", "description": "将指定 xlsx 保存为发货单模板.xlsx"}, {"name": "展示模板", "description": "展示可编辑词条与字段映射"}, {"name": "介绍功能", "description": "介绍抬头、业务字段与价格计算逻辑"}]},
            {"id": "excel_decompose", "name": "Excel 模板分解", "description": "自动分解 Excel 结构，提取表头、可编辑词条与金额字段", "category": "excel",
             "actions": [{"name": "分解模板", "description": "输出表头、词条、样例行与金额字段"}]},
            {"id": "excel_analyzer", "name": "Excel 模板分析", "description": "深度分析Excel模板结构，识别可编辑区域、表头、数据区、汇总区、合并单元格", "category": "excel",
             "actions": [{"name": "分析模板", "description": "分析Excel模板结构和可编辑区域"}, {"name": "提取结构", "description": "提取模板的表头、数据区、汇总区信息"}]},
            {"id": "excel_toolkit", "name": "Excel 工具箱", "description": "查看Excel内容、合并单元格、样式信息，分析表格结构", "category": "excel",
             "actions": [{"name": "查看内容", "description": "查看Excel文件内容"}, {"name": "合并单元格", "description": "获取合并单元格信息"}, {"name": "样式信息", "description": "获取单元格样式"}]},
            {"id": "ocr", "name": "图片 OCR", "description": "识别图片中的文字", "category": "ocr",
             "actions": [{"name": "文字识别", "description": "上传图片识别文字"}, {"name": "结构化提取", "description": "从图片中提取结构化数据"}]},
            {"id": "wechat", "name": "微信任务", "description": "扫描微信消息，识别订单和发货单", "category": "wechat",
             "actions": [{"name": "扫描消息", "description": "扫描微信消息"}, {"name": "查看任务", "description": "查看待处理任务"}]},
        ]
        return jsonify({"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tool-categories', methods=['GET'])
@swag_from({
    'summary': '获取工具分类',
    'description': '获取工具分类列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'categories': {'type': 'array'}
                }
            }
        }
    }
})
def get_tool_categories():
    """获取工具分类列表"""
    try:
        categories = [
            {"id": 1, "category_name": "产品管理", "category_key": "products", "description": "产品与型号管理", "icon": "📦", "sort_order": 1, "is_active": True},
            {"id": 2, "category_name": "客户/购买单位", "category_key": "customers", "description": "客户信息管理", "icon": "👥", "sort_order": 2, "is_active": True},
            {"id": 3, "category_name": "出货单", "category_key": "orders", "description": "订单与发货单管理", "icon": "📋", "sort_order": 3, "is_active": True},
            {"id": 4, "category_name": "标签打印", "category_key": "print", "description": "标签打印管理", "icon": "🖨️", "sort_order": 4, "is_active": True},
            {"id": 5, "category_name": "原材料仓库", "category_key": "materials", "description": "原材料库存管理", "icon": "🏭", "sort_order": 5, "is_active": True},
            {"id": 6, "category_name": "Excel 处理", "category_key": "excel", "description": "Excel 模板与数据处理", "icon": "📊", "sort_order": 6, "is_active": True},
            {"id": 7, "category_name": "图片 OCR", "category_key": "ocr", "description": "图片文字识别", "icon": "🔍", "sort_order": 7, "is_active": True},
            {"id": 8, "category_name": "数据库管理", "category_key": "database", "description": "数据库备份与恢复", "icon": "💾", "sort_order": 8, "is_active": True},
            {"id": 9, "category_name": "系统设置", "category_key": "system", "description": "系统配置与管理", "icon": "⚙️", "sort_order": 9, "is_active": True},
            {"id": 10, "category_name": "微信任务", "category_key": "wechat", "description": "微信消息处理", "icon": "💬", "sort_order": 10, "is_active": True},
        ]
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        logger.error(f"获取工具分类失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tools/execute', methods=['POST'])
@swag_from({
    'summary': '执行工具',
    'description': '执行工具操作，支持 database 和 system 工具的实际操作\n\n支持的工具和操作：\n- database: backup, restore, list, delete\n- system: get_startup_config, enable_startup, disable_startup, get_system_info, get_printer_config, set_default_printer\n- 其他工具主要返回重定向 URL',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'tool_id': {'type': 'string', 'description': '工具 ID', 'enum': ['products', 'customers', 'orders', 'database', 'system', 'print', 'materials', 'ocr', 'wechat', 'excel_decompose', 'shipment_template', 'shipment_generate']},
                    'action': {'type': 'string', 'description': '操作类型', 'enum': ['view', 'backup', 'restore', 'list', 'delete', 'get_startup_config', 'enable_startup', 'disable_startup', 'get_system_info', 'get_printer_config', 'set_default_printer']},
                    'params': {
                        'type': 'object',
                        'description': '操作参数',
                        'properties': {
                            'backup_file': {'type': 'string', 'description': '备份文件路径（用于 restore 和 delete 操作）'},
                            'printer_name': {'type': 'string', 'description': '打印机名称（用于 set_default_printer 操作）'},
                            'order_text': {'type': 'string', 'description': '订单文本（用于 shipment_generate 操作）'}
                        }
                    }
                },
                'required': ['tool_id', 'action']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'result': {'type': 'object'},
                    'message': {'type': 'string'},
                    'redirect': {'type': 'string', 'description': '重定向 URL（仅部分工具）'},
                    'data': {'type': 'object', 'description': '返回数据（system 工具）'},
                    'backups': {'type': 'array', 'description': '备份列表（database list 操作）'},
                    'count': {'type': 'integer', 'description': '数量（database list 操作）'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def execute_tool():
    """执行工具操作"""
    try:
        from flask import request
        data = request.get_json()
        
        # 详细日志：记录请求数据
        logger.info(f"[DEBUG] /api/tools/execute 收到请求 - data: {data}")
        
        if not data:
            logger.error(f"[DEBUG] /api/tools/execute 请求数据为空")
            return jsonify({"success": False, "message": "未收到数据"}), 400
        
        tool_id = data.get('tool_id')
        action = data.get('action', 'view')
        params = data.get('params') or {}
        
        # 记录关键参数
        logger.info(f"[DEBUG] tool_id={tool_id}, action={action}, params_keys={list(params.keys())}")
        if 'order_text' in params:
            logger.info(f"[DEBUG] order_text={params.get('order_text')[:200] if params.get('order_text') else None}")
        
        if tool_id == 'products':
            from app.routes.products import products_bp
            effective_action = action
            if action in ('执行', 'exec', 'run', 'execute'):
                effective_action = params.get('action', 'view')

            keyword = (params.get("keyword") or "").strip()
            unit_name = (params.get("unit_name") or "").strip()
            model_number = (params.get("model_number") or "").strip()
            tin_spec = (params.get("tin_spec") or "").strip()

            search_verbs = ['search', 'query', 'find', '查找', '查询', '搜索']
            is_search = (effective_action in search_verbs) or keyword

            if is_search and keyword:
                return jsonify({
                    "success": True,
                    "redirect": f"/console?view=products&keyword={keyword}",
                    "message": f"已按关键词检索产品：{keyword}",
                    "data": {
                        "keyword": keyword,
                        "unit_name": unit_name,
                        "model_number": model_number,
                        "tin_spec": tin_spec
                    }
                })
            if effective_action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=products"})
            return jsonify({"success": True, "message": "产品管理"})
        
        elif tool_id == 'customers':
            # pro 模式下 action 往往是固定的“执行”，但 TaskAgent/前端 params 里会携带真正的子动作（如 search/query）
            effective_action = action
            if (str(action) or "") in ("执行", "exec", "run") and params.get("action"):
                effective_action = params.get("action")

            # 不同上游/模型可能不会把自然语言放在 order_text 里，这里把常见字段都拼一下，提升意图识别鲁棒性。
            order_text = (
                params.get("order_text")
                or params.get("text")
                or params.get("message")
                or params.get("content")
                or ""
            ).strip()
            lower_text = order_text.lower()

            # 把 params 的值也一起纳入意图判断（避免 order_text 为空导致误走 search/query redirect）
            param_blob = " ".join([str(v) for v in (params or {}).values() if v is not None]).strip()
            lower_param_blob = param_blob.lower()

            has_add_verb = (
                any(v in order_text for v in ["添加", "新增", "创建", "新建", "增加"])
                or any(v in lower_text for v in ["add", "create", "new"])
                or any(v in param_blob for v in ["添加", "新增", "创建", "新建", "增加"])
                or any(v in lower_param_blob for v in ["add", "create", "new"])
            )
            has_del_verb = (
                any(v in order_text for v in ["删除", "移除", "去掉"])
                or any(v in lower_text for v in ["delete", "remove", "del"])
                or any(v in param_blob for v in ["删除", "移除", "去掉"])
                or any(v in lower_param_blob for v in ["delete", "remove", "del"])
            )

            keyword = (params.get("keyword") or "").strip()
            # 如果是“检索/搜索”但上游没给 keyword，就尽量用 params 里的名称兜底
            # 注意：一旦用户明确表达删除（has_del_verb），删除应当优先覆盖 search/query redirect。
            if effective_action in ("search", "query") and not keyword and not has_add_verb and not has_del_verb:
                keyword = (
                    params.get("unit_name")
                    or params.get("name")
                    or params.get("customer_name")
                    or ""
                ).strip()
            # 如果自然语言包含“添加/新增/创建”，即便 AI 把 action 判成 search/query，也应优先创建。
            if effective_action in ('search', 'query') and keyword and not has_add_verb and not has_del_verb:
                logger.info("customers: redirect search/query keyword=%s", keyword)
                return jsonify({"success": True, "redirect": f"/console?view=customers&keyword={keyword}", "message": f"已按关键词检索客户：{keyword}"})
            if effective_action == 'view' and not has_add_verb and not has_del_verb:
                logger.info("customers: redirect view")
                return jsonify({"success": True, "redirect": "/console?view=customers"})

            logger.info(
                "customers: attempt create? effective_action=%s has_add_verb=%s order_text_len=%s params_keys=%s",
                effective_action,
                has_add_verb,
                len(order_text or ""),
                list(params.keys()),
            )

            # 聊天/工具侧删除：支持 action=delete/remove/del，幂等删除（不存在也返回 success）
            if effective_action in ("delete", "remove", "del") or has_del_verb:
                from app.db.models import PurchaseUnit
                from app.infrastructure.repositories.customer_repository_impl import (
                    get_customers_session,
                )

                target_id = params.get("customer_id") or params.get("id") or params.get("unit_id")
                target_name = (params.get("customer_name") or params.get("unit_name") or params.get("name") or "").strip()

                # 尽量从自然语言中提取名称：如“删除客户/购买单位叫XX”
                if not target_name and order_text:
                    import re

                    # 支持：包含“联系人/电话/地址”后缀的删除句式
                    # 例：删除购买单位小王公司联系人王总  -> 提取“小王公司”
                    m = re.search(
                        r"(?:删除|移除)?\s*(?:客户|购买单位|单位)\s*(?:叫|是|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,60}?)"
                        r"(?=(?:联系人|电话|手机|手机号|联系电话|联系号码|地址|住址)|\s*$)",
                        order_text
                    )
                    if m:
                        target_name = (m.group(1) or "").strip()

                session = get_customers_session()
                deleted_count = 0
                try:
                    if target_id:
                        try:
                            tid = int(target_id)
                            deleted = session.query(PurchaseUnit).filter(PurchaseUnit.id == tid).delete(synchronize_session=False)
                            deleted_count = int(deleted or 0)
                        except Exception:
                            deleted_count = 0
                    elif target_name:
                        deleted = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == target_name).delete(synchronize_session=False)
                        deleted_count = int(deleted or 0)
                        if deleted_count == 0 and target_name:
                            try:
                                from app.infrastructure.lookups.purchase_unit_resolver import (
                                    resolve_purchase_unit,
                                )
                                resolved = resolve_purchase_unit(target_name)
                                if resolved and getattr(resolved, "unit_name", None) and resolved.unit_name != target_name:
                                    deleted = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == resolved.unit_name).delete(synchronize_session=False)
                                    deleted_count = int(deleted or 0)
                            except Exception:
                                pass

                    if target_id or target_name:
                        try:
                            session.commit()
                        except Exception:
                            pass

                    return jsonify({
                        "success": True,
                        "message": "删除成功" if deleted_count > 0 else "删除成功（未找到匹配记录）",
                        "deleted_count": deleted_count,
                    }), 200
                finally:
                    session.close()

            # 聊天创建购买单位兜底：
            # 当用户表达“添加客户/购买单位 + 名称/联系人/电话/地址”时，直接写入 purchase_units。
            # 这与前端 pro-feature-widget 里 POST /api/purchase_units 的字段对齐。
            should_create_purchase_unit = str(effective_action) in {
                "add", "create", "添加", "新增", "添加客户", "添加购买单位", "create_purchase_unit"
            } or has_add_verb

            # 补充客户信息处理（他/她/它的 联系人/电话/地址）
            should_supplement = str(effective_action) in {"supplement", "补充"} or params.get("field_name")

            if should_supplement:
                from app.db.models import PurchaseUnit
                from app.infrastructure.repositories.customer_repository_impl import (
                    get_customers_session,
                )
                from app.services import get_task_context_service

                ctx = get_task_context_service()
                user_id = params.get("user_id") or request.headers.get("X-User-ID", "default")

                last_customer = ctx.get_last_customer(user_id)
                field_name = params.get("field_name", "")
                field_value = params.get("field_value", "")

                if not field_name and order_text:
                    m = re.search(r"(?:联系人|联系电话|电话|手机|地址)\s*(?:是|：|:)?\s*(.{1,30})", order_text)
                    if m:
                        field_name = "contact_person"
                        field_value = m.group(1).strip()

                if not field_value and order_text:
                    if field_name == "contact_person":
                        m = re.search(r"(?:联系人|联系人是)\s*(?:是|：|:)?\s*([^\s，,。]{1,20})", order_text)
                        if m:
                            field_value = m.group(1).strip()
                    elif field_name in ("contact_phone", "contact_address"):
                        m = re.search(r"(?:电话|手机|地址)\s*(?:是|：|:)?\s*([^\s，,。]{1,50})", order_text)
                        if m:
                            field_value = m.group(1).strip()

                if not last_customer and not field_value:
                    return jsonify({"success": False, "message": "请先告诉我要补充哪个客户的联系人信息，例如：添加客户七彩乐园"}), 400

                target_name = last_customer.get("customer_name") if last_customer else None
                if not target_name:
                    m = re.search(r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})", order_text)
                    if m:
                        target_name = (m.group(1) or "").strip()

                if not target_name:
                    return jsonify({"success": False, "message": "请告诉我要补充哪个客户的联系人信息"}), 400

                field_map = {
                    "contact_person": "联系人",
                    "contact_phone": "联系电话",
                    "contact_address": "地址",
                }
                field_label = field_map.get(field_name, field_name)

                session = get_customers_session()
                try:
                    customer = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == target_name).first()
                    if not customer:
                        return jsonify({"success": False, "message": f"未找到客户：{target_name}"}), 404

                    if field_name == "contact_person":
                        customer.contact_person = field_value
                    elif field_name == "contact_phone":
                        customer.contact_phone = field_value
                    elif field_name == "contact_address":
                        customer.address = field_value

                    session.commit()
                    session.refresh(customer)

                    return jsonify({
                        "success": True,
                        "message": f"已为 {target_name} 补充 {field_label}：{field_value}",
                        "data": {
                            "id": customer.id,
                            "customer_name": customer.unit_name,
                            "contact_person": customer.contact_person,
                            "contact_phone": customer.contact_phone,
                            "contact_address": customer.address,
                        }
                    }), 200
                finally:
                    session.close()

            if should_create_purchase_unit:
                import re
                from datetime import datetime

                from app.application import CustomerApplicationService, get_customer_app_service
                from app.db.session import get_db

                unit_name = (params.get("unit_name") or params.get("name") or params.get("customer_name") or "").strip()
                contact_person = (params.get("contact_person") or "").strip()
                contact_phone = (params.get("contact_phone") or "").strip()
                address = (params.get("address") or params.get("contact_address") or "").strip()

                # 兼容：有些模型/上游会把“购买单位 + 联系人”拼成一个字段，
                # 例如：unit_name = "七彩乐园联系人向总"。
                # 这里对 unit_name 做关键词前截断，避免把联系人尾部污染客户名。
                if unit_name:
                    m_unit = re.match(
                        r"^(.+?)(?=(联系人|电话|手机|手机号|联系电话|联系号码|地址|住址|联系地址|$))",
                        unit_name
                    )
                    if m_unit and (m_unit.group(1) or "").strip():
                        unit_name = m_unit.group(1).strip()

                # 从自然语言中尽量提取字段（例如：“添加一个客户叫七彩乐园，联系人是向总”）
                if not unit_name and order_text:
                    m = re.search(r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})", order_text)
                    if m:
                        unit_name = (m.group(1) or "").strip()

                if not contact_person and order_text:
                    m = re.search(r"(?:联系人|联系人是)\s*(?:是|：)?\s*([^\s，,。]{1,20})", order_text)
                    if m:
                        contact_person = (m.group(1) or "").strip()

                if not contact_phone and order_text:
                    m = re.search(r"(?:电话|手机|手机号|联系电话|联系号码)\s*(?:是|：)?\s*(\d{5,20})", order_text)
                    if m:
                        contact_phone = (m.group(1) or "").strip()

                if not address and order_text:
                    m = re.search(r"(?:地址|住址|联系地址)\s*(?:是|：)?\s*([^，,。]{2,80})", order_text)
                    if m:
                        address = (m.group(1) or "").strip()

                logger.info(
                    "customers: create extracted unit_name=%s contact_person=%s contact_phone=%s address=%s",
                    unit_name,
                    contact_person,
                    contact_phone,
                    address,
                )

                if not unit_name:
                    logger.warning("customers: create skipped due to missing unit_name")
                    return jsonify({"success": False, "message": "缺少购买单位参数（unit_name/name）"}), 400

                # 为了让聊天添加在界面上可见，同时保证发货单能解析：
                # - `customers` 表：系统唯一来源（发货单解析也只从 customers 解析）

                # 1) 写入 customers（用于前端显示 & 供发货单解析）
                customer_data = {
                    "customer_name": unit_name,
                    "contact_person": contact_person or None,
                    "contact_phone": contact_phone or None,
                    "contact_address": address or None,
                }
                customer_service = get_customer_app_service()
                customer_result = customer_service.create(customer_data)
                if customer_result.get("success"):
                    logger.info("customers: customer created customer_name=%s", unit_name)

                    from app.services import get_task_context_service
                    ctx = get_task_context_service()
                    user_id = request.headers.get("X-User-ID", "default")
                    ctx.set_last_customer(user_id, {
                        "customer_name": unit_name,
                        "contact_person": contact_person,
                        "contact_phone": contact_phone,
                        "contact_address": address,
                    })

                    return jsonify(customer_result), 201

                # 幂等：客户已存在也视为成功（避免前端把“已存在”当失败）
                msg = customer_result.get("message") or ""
                if "客户名称已存在" in msg:
                    from app.db.models import PurchaseUnit
                    session = get_customers_session()
                    try:
                        exists = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == unit_name).first()
                        customer_id = exists.id if exists else None
                        return jsonify({
                            "success": True,
                            "message": "已存在",
                            "data": {
                                "id": customer_id,
                                "customer_name": unit_name,
                                "contact_person": (exists.contact_person if exists else None),
                                "contact_phone": (exists.contact_phone if exists else None),
                                "contact_address": (exists.address if exists else None),
                            }
                        }), 201
                    finally:
                        session.close()

                return jsonify(customer_result), 400

            return jsonify({"success": True, "message": "客户管理"})
        
        elif tool_id == 'orders':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment-orders"})
            return jsonify({"success": True, "message": "出货单"})
        
        elif tool_id == 'shipment_generate':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment"})
            
            # 真正调用发货单生成 API
            try:
                # 从 params 中获取订单文本或产品信息
                order_text = params.get('order_text', '')
                
                logger.info(f"收到发货单生成请求：order_text={order_text}")

                if order_text and order_text.strip():
                    # 使用 XCAGI 自己的发货单服务层
                    from sqlalchemy.orm import Session

                    from app.bootstrap import get_shipment_app_service
                    from app.db.models import Product
                    from app.db.session import get_db

                    # 解析订单文本（简单解析：提取单位名、产品、数量、规格）
                    # 格式示例："发货单七彩乐园 1 桶 9803 规格 12"
                    logger.info(f"[DEBUG] 开始解析订单文本：{order_text[:200]}")
                    parsed_result = _parse_order_text(order_text)
                    logger.info(f"[DEBUG] 订单解析结果：{parsed_result}")

                    if not parsed_result.get('success'):
                        error_msg = parsed_result.get('message', '')
                        logger.error(f"[DEBUG] 订单文本解析失败：order_text={order_text[:200]}, error={error_msg}")
                        if any(kw in order_text for kw in ['产品列表', '产品库', '商品列表', '查看产品']):
                            return jsonify({
                                "success": False,
                                "message": "您是想查看产品列表吗？请使用「产品列表」功能。",
                                "redirect": "/console?view=products",
                                "suggested_action": "products"
                            }), 200
                        logger.error(f"[DEBUG] 返回 400 错误，错误消息：{error_msg}")
                        return jsonify(parsed_result), 400
                    
                    unit_name = parsed_result['unit_name']
                    products = parsed_result['products']
                    
                    # 调用 DDD 应用服务生成发货单
                    app_service = get_shipment_app_service()
                    result = app_service.generate_shipment_document(
                        unit_name=unit_name,
                        products=products,
                        template_name=None,
                    )
                    
                    logger.info(f"发货单生成结果：{result}")
                    return jsonify(result)
                
                # order_text 为空时的错误处理
                logger.error(f"[DEBUG] 缺少 order_text 参数，params={params}")
                return jsonify({
                    "success": False,
                    "message": "缺少订单文本参数，请提供订单信息"
                }), 400
                
            except Exception as e:
                logger.error(f"生成发货单失败：{e}", exc_info=True)
                return jsonify({
                    "success": False,
                    "message": f"生成失败：{str(e)}"
                }), 500
        
        elif tool_id == 'print':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=print"})
            return jsonify({"success": True, "message": "标签打印"})
        
        elif tool_id == 'materials':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=materials"})
            return jsonify({"success": True, "message": "原材料仓库"})
        
        elif tool_id == 'ocr':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=ocr"})
            return jsonify({"success": True, "message": "图片 OCR"})
        
        elif tool_id == 'wechat':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=wechat-contacts"})
            return jsonify({"success": True, "message": "微信任务"})
        
        elif tool_id == 'excel_decompose':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=excel"})
            return jsonify({"success": True, "message": "Excel 模板分解"})

        elif tool_id == 'excel_analyzer':
            file_path = params.get('file_path')
            sheet_name = params.get('sheet_name')
            output_json = params.get('output_json')

            if not file_path:
                return jsonify({
                    "success": False,
                    "message": "缺少参数：file_path（Excel文件路径）"
                }), 400

            try:
                from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
                    ExcelAnalyzerSkill,
                    get_excel_analyzer_skill,
                )
                skill = get_excel_analyzer_skill()
                result = skill.execute(file_path=file_path, sheet_name=sheet_name, output_json=output_json)
                return jsonify(result)
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "Excel分析技能未正确安装，请检查openpyxl库"
                }), 500
            except Exception as e:
                logger.error(f"Excel Analyzer执行失败: {e}")
                return jsonify({
                    "success": False,
                    "message": f"分析失败: {str(e)}"
                }), 500

        elif tool_id == 'excel_toolkit':
            file_path = params.get('file_path')
            sheet_name = params.get('sheet_name')
            toolkit_action = params.get('action', 'view')

            if not file_path:
                return jsonify({
                    "success": False,
                    "message": "缺少参数：file_path（Excel文件路径）"
                }), 400

            try:
                from app.infrastructure.skills.excel_toolkit.excel_toolkit import (
                    ExcelToolkitSkill,
                    get_excel_toolkit_skill,
                )
                skill = get_excel_toolkit_skill()
                result = skill.execute(file_path=file_path, action=toolkit_action, sheet_name=sheet_name)
                return jsonify(result)
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "Excel工具技能未正确安装，请检查openpyxl库"
                }), 500
            except Exception as e:
                logger.error(f"Excel Toolkit执行失败: {e}")
                return jsonify({
                    "success": False,
                    "message": f"执行失败: {str(e)}"
                }), 500

        elif tool_id == 'shipment_template':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=template-preview"})
            return jsonify({"success": True, "message": "发货单模板"})
        
        elif tool_id == 'database':
            from app.services import get_database_service
            
            db_service = get_database_service()

            # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
            if action in (None, '', 'view'):
                return jsonify({"success": True, "message": "数据库管理"}), 200
            
            if action == 'backup':
                result = db_service.backup_database()
                return jsonify(result)
            
            elif action == 'restore':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.restore_database(backup_file)
                return jsonify(result)
            
            elif action == 'list':
                result = db_service.list_backups()
                return jsonify(result)
            
            elif action == 'delete':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.delete_backup(backup_file)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的数据库操作：{action}"
                }), 400
        
        elif tool_id == 'system':
            from app.services import get_system_service
            
            system_service = get_system_service()

            # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
            if action in (None, '', 'view'):
                return jsonify({"success": True, "message": "系统设置"}), 200
            
            if action == 'get_startup_config':
                result = system_service.get_startup_config()
                return jsonify({"success": True, "data": result})
            
            elif action == 'enable_startup':
                result = system_service.enable_startup()
                return jsonify(result)
            
            elif action == 'disable_startup':
                result = system_service.disable_startup()
                return jsonify(result)
            
            elif action == 'get_system_info':
                result = system_service.get_system_info()
                return jsonify({"success": True, "data": result})
            
            elif action == 'get_printer_config':
                result = system_service.get_printer_config()
                return jsonify(result)
            
            elif action == 'set_default_printer':
                printer_name = params.get('printer_name')
                if not printer_name:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：printer_name"
                    }), 400
                result = system_service.set_default_printer(printer_name)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的系统操作：{action}"
                }), 400
        
        elif tool_id == 'upload_file':
            # upload_file 是“让用户上传文件”的 UI 引导工具。
            # 该接口本身不执行解析/入库，仅返回前端可触发上传浮层的提示文案。
            msg = "请上传文件以继续（Excel / 图片 / CSV 均可）。"
            return jsonify({"success": True, "message": msg}), 200
        
        return jsonify({"success": False, "message": f"未知工具: {tool_id}"}), 400
        
    except Exception as e:
        logger.error(f"执行工具失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500