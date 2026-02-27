#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发货单解析服务 - 智能解析自然语言订单
支持解析格式如："蕊芯PU 哑光黑面漆20公斤"
"""

import re
import sqlite3
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedOrder:
    """解析后的订单信息"""
    purchase_unit: str = ""  # 购买单位
    product_name: str = ""   # 产品名称
    model_number: str = ""   # 产品型号
    quantity_kg: float = 0.0  # 数量（公斤）
    quantity_tins: int = 0   # 数量（桶）
    tin_spec: float = 0.0    # 桶规格（kg/桶）
    unit_price: float = 0.0  # 单价
    amount: float = 0.0      # 金额
    raw_text: str = ""       # 原始文本
    products: List[Dict] = field(default_factory=list)  # 多产品列表
    parsed_data: Dict = field(default_factory=dict)  # 解析详情
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def is_valid(self) -> bool:
        """检查是否有效"""
        return bool(self.products) and len(self.products) > 0


class ShipmentParser:
    """发货单解析器"""
    
    # 常见购买单位列表
    KNOWN_PURCHASE_UNITS = [
        "蕊芯家私1", "蕊芯家私", "蕊芯", "蕊芯测试",
        "七彩乐园", "七彩乐园家私",
        "金汉武", "金汉武家私",
        "侯雪梅",
        "刘英",
        "国圣化工", "国圣",
        "宗南",
        "宜榢",
        "小洋杨总",
        "尹玉华",
        "志泓",
        "新旺博旺",
        "温总",
        "澜宇电视柜",
        "现金",
        "迎扬李总",
        "邻居杨总",
        "邻居贾总",
    ]
    
    # 常见桶规格（kg）
    COMMON_TIN_SPECS = [1.0, 5.0, 10.0, 15.0, 18.0, 20.0, 25.0, 180.0]
    
    def __init__(self, db_path: str = None):
        """初始化解析器"""
        # 使用当前目录中的数据库文件
        if db_path is None:
            # 使用当前目录的products.db
            self.db_path = "products.db"
        else:
            self.db_path = db_path
        
        # 从数据库加载购买单位
        self._purchase_units = self._load_purchase_units_from_db()
        
        # 单位数据库目录
        self.unit_database_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unit_databases')
        print(f"单位数据库目录: {self.unit_database_dir}")
    
    def parse(self, text: str, custom_mode: bool = None, number_mode: bool = False) -> ParsedOrder:
        """
        解析订单文本
        支持格式：
        - "蕊芯PU哑光黑面漆20公斤"
        - "蕊芯 PU净味面漆稀释剂 180KG 桶装20kg"
        - "蕊芯 A1(553) PU净味哑光浅蓝色漆 180KG"
        - "七彩家园P1白底10桶，P1稀释剂180kg1桶，P哑光白面漆5桶"
        - "温总型号NC50F，NC哑光清面漆3桶规格25单价14.5，自定义"
        """
        text = text.strip()
        result = ParsedOrder(raw_text=text)
        
        try:
            # 只有当custom_mode明确为True时才使用自定义模式
            is_custom = custom_mode if custom_mode is not None else False
            # 编号模式
            is_number_mode = number_mode
            
            # 1. 提取购买单位
            result.purchase_unit = self._extract_purchase_unit(text)
            
            # 2. 按逗号分割多个产品
            product_items = self._split_products(text, result.purchase_unit)
            
            # 3. 解析每个产品
            all_products = []
            total_kg = 0.0
            total_tins = 0
            total_amount = 0.0
            
            for item_text in product_items:
                if not item_text.strip():
                    continue
                
                # 移除"自定义"关键字，避免影响解析
                item_text = item_text.replace("自定义", "").strip()
                    
                product = self._parse_single_product(item_text, is_custom, text, number_mode)
                if product:
                    all_products.append(product)
                    total_kg += product.get("quantity_kg", 0)
                    total_tins += product.get("quantity_tins", 0)
                    total_amount += product.get("amount", 0)
            
            result.products = all_products
            
            # 4. 保存汇总信息（兼容旧逻辑）
            if all_products:
                first_product = all_products[0]
                result.product_name = first_product.get("name", "")
                result.model_number = first_product.get("model_number", "")
                result.quantity_kg = total_kg
                result.quantity_tins = total_tins
                result.tin_spec = first_product.get("tin_spec", 10.0)
                result.unit_price = first_product.get("unit_price", 0)
                result.amount = total_amount
            
            # 5. 保存解析详情
            result.parsed_data = {
                "purchase_unit": result.purchase_unit,
                "product_name": result.product_name,
                "model_number": result.model_number,
                "quantity_kg": result.quantity_kg,
                "quantity_tins": result.quantity_tins,
                "tin_spec": result.tin_spec,
                "unit_price": result.unit_price,
                "amount": result.amount,
                "products": all_products,
                "parse_time": datetime.now().isoformat(),
                "is_custom": is_custom
            }
            
            return result
            
        except Exception as e:
            logger.error(f"解析订单失败: {e}")
            result.parsed_data = {"error": str(e)}
            return result
    
    def _split_products(self, text: str, purchase_unit: str) -> List[str]:
        """分割多个产品"""
        # 移除购买单位
        working_text = text
        if purchase_unit:
            working_text = working_text.replace(purchase_unit, "").strip()
        
        # 特殊处理 "规格数字产品名:数量桶规格数字" 格式
        # 如："规格28KGPE稀释剂:1桶，规格180KG"
        if '规格' in working_text and 'PE' in working_text:
            comma_pos = working_text.find('，')
            if comma_pos > 0:
                first_part = working_text[:comma_pos]  # "Pe白底漆10桶"
                second_part = working_text[comma_pos+1:]  # "规格28KGPE稀释剂:1桶，规格180KG"
                
                # 查找PE稀释剂的位置
                pe_pos = second_part.find('PE稀释剂')
                if pe_pos > 0:
                    # 找到PE稀释剂前的规格信息
                    spec_match = re.search(r'规格(\d+)', second_part[:pe_pos])
                    if spec_match:
                        spec = spec_match.group(1)
                        # 第一产品：Pe白底漆10桶，规格28KG
                        product1 = first_part + f"，规格{spec}KG"
                        
                        # 第二产品：PE稀释剂:1桶，规格180KG
                        # 查找规格180KG
                        spec180_match = re.search(r'规格(\d+)', second_part[pe_pos:])
                        if spec180_match:
                            spec180 = spec180_match.group(1)
                            product2 = f"PE稀释剂:1桶，规格{spec180}KG"
                            return [product1, product2]
        
        # 特殊处理复杂格式：支持逗号和冒号分隔的产品
        if ',' in working_text and ':' in working_text:
            # 找到第一个逗号
            comma_pos = working_text.find('，')
            if comma_pos > 0:
                # 第一部分：Pe白底漆10桶
                first_part = working_text[:comma_pos]
                
                # 第二部分：包含多个产品的复杂文本
                second_part = working_text[comma_pos+1:]
                
                products = [first_part]
                
                # 特殊处理冒号分隔的产品
                # 使用正则表达式匹配 "产品名:数量桶规格数字" 模式
                
                # 查找PE开头的稀释剂产品
                pe_match = re.search(r'PE稀释剂:.*?规格(\d+)', second_part)
                if pe_match:
                    spec = pe_match.group(1)
                    products.append(f"PE稀释剂:1桶规格{spec}")
                
                # 查找PE白底稀料/PE白底漆稀料
                pe_white_thinner_match = re.search(r'PE白底漆?稀料:.*?规格(\d+)', second_part)
                if pe_white_thinner_match:
                    spec = pe_white_thinner_match.group(1)
                    products.append(f"PE白底漆稀料:1桶规格{spec}")
                else:
                    # 尝试匹配 "PE白底稀料1桶规格数字"
                    pe_white_simple_match = re.search(r'PE白底稀料(\d+桶规格\d+)', second_part)
                    if pe_white_simple_match:
                        tin_spec_info = pe_white_simple_match.group(1)
                        products.append(f"PE白底漆稀料:{tin_spec_info}")
                
                # 查找其他冒号产品
                # 匹配 "24-4-8 哑光银珠:1桶规格20" 模式
                other_matches = re.findall(r'([^:,]+?):(\d+桶(?:规格\d+)?)', second_part)
                for match in other_matches:
                    product_name = match[0].strip()
                    quantity_info = match[1].strip()
                    
                    # 跳过已经添加的PE稀释剂
                    if "PE" in product_name:
                        continue
                    
                    # 如果不是数字开头的产品名，添加到产品列表
                    if not re.match(r'^\d', product_name):
                        products.append(f"{product_name}:{quantity_info}")
                
                # 特殊处理：查找 "桶规格数字" 格式的遗漏产品
                tin_spec_matches = re.findall(r'(\d+桶规格\d+)([A-Z][^:,]*?)(?::|$)', second_part)
                for match in tin_spec_matches:
                    tin_spec_info = match[0]
                    product_name = match[1].strip()
                    
                    # 跳过PE产品（已经处理）
                    if "PE" in product_name:
                        continue
                    
                    if product_name and not any(product_name in p for p in products):
                        products.append(f"{product_name}:{tin_spec_info}")
                
                # 移除重复产品
                unique_products = []
                for product in products:
                    if product not in unique_products:
                        unique_products.append(product)
                
                return unique_products
        
        # 默认分割逻辑（按逗号）
        items = re.split(r'[,，]', working_text)
        
        products = []
        pending_product = None  # 待关联规格的产品
        
        for item in items:
            item = item.strip()
            if not item:
                continue
                
            # 如果是规格条目，关联到待处理的产品
            spec_match = re.match(r'规格(\d+)$', item)
            if spec_match and pending_product:
                spec = spec_match.group(1)
                # 将规格追加到待处理产品
                products.append(f"{pending_product}规格{spec}")
                pending_product = None
                continue
            
            # 如果是 "PE白底稀料1桶" 格式，先添加到待处理
            pe_white_match = re.match(r'PE白底稀料(\d+桶)$', item)
            if pe_white_match:
                pending_product = f"PE白底漆稀料{pe_white_match.group(1)}"
                continue
            
            # 检查是否是 "PE白底漆稀料1桶规格数字" 格式
            if re.match(r'^规格\d+', item):
                continue
            
            if item:
                products.append(item)
        
        # 如果还有待处理的产品没有规格，添加它
        if pending_product:
            products.append(pending_product)
        
        # 如果没有分割成功，返回原文本作为单个产品
        if not products:
            products = [working_text]
        
        return products
    
    def _parse_single_product(self, text: str, is_custom: bool = False, original_text: str = "", number_mode: bool = False) -> Optional[Dict]:
        """解析单个产品"""
        try:
            # 从原始文本中提取购买单位
            purchase_unit = self._extract_purchase_unit(original_text)
            # 尝试从数据库匹配，传递购买单位和编号模式
            db_match = self._match_product_from_db(text, purchase_unit, number_mode)
            
            product = {
                "name": "",
                "model_number": "",
                "quantity_kg": 0.0,
                "quantity_tins": 0,
                "tin_spec": 10.0,
                "unit_price": 0.0,
                "amount": 0.0
            }
            
            # 提取数量信息（统一处理）
            quantity_info = self._extract_quantity(text)
            
            # 提取单价信息
            unit_price = 0.0
            # 直接使用正则表达式提取，支持多种格式
            price_patterns = [
                r'单价(\d+(?:\.\d+)?)',  # 单价14.5
                r'(?:价格|售价|单价)[：:]*\s*(\d+(?:\.\d+)?)',  # 价格：14.5
                r'(?:单价|价格)(\d+(?:\.\d+)?)元?',  # 单价14.5元
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        unit_price = float(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue
            
            # 提取规格信息
            tin_spec = 10.0
            if "规格" in text:
                spec_match = re.search(r'规格(\d+(?:\.\d+)?)', text)
                if spec_match:
                    tin_spec = float(spec_match.group(1))
            
            if db_match and not is_custom:  # 只有在非自定义模式下才使用数据库信息
                # 数据库匹配到产品，使用数据库信息
                product["name"] = db_match.get("name", "")
                product["model_number"] = db_match.get("model_number", "")
                product["unit_price"] = db_match.get("price", unit_price)  # 使用数据库价格，否则使用提取的价格
                product["quantity_kg"] = quantity_info["kg"]
                product["quantity_tins"] = quantity_info["tins"]
                product["tin_spec"] = tin_spec if tin_spec != 10.0 else quantity_info["tin_spec"]  # 优先使用提取的规格
            elif is_custom:
                # 自定义模式，使用用户输入的产品信息
                # 提取产品名称，保留尽可能多的原始信息
                # 先移除数量和单价信息
                temp_text = text
                
                # 移除单价信息
                temp_text = re.sub(r'\s*单价\d+(?:\.\d+)?', '', temp_text)
                
                # 移除桶数信息
                temp_text = re.sub(r'\d+\s*桶', '', temp_text)
                
                # 移除规格信息
                temp_text = re.sub(r'规格\d+(?:\.\d+)?', '', temp_text)
                
                # 移除数量信息（kg等）
                temp_text = re.sub(r'\d+(?:\.\d+)?\s*(?:kg|公斤|千克|KG|K)', '', temp_text, flags=re.IGNORECASE)
                
                # 清理并提取产品名称
                product_name = temp_text.strip()
                product["name"] = product_name
                
                # 提取型号（支持"编号"和"型号"关键字）
                model_number = ""
                
                # 1. 从当前产品文本中提取
                model_patterns = [
                    r'(型号|编号)[：:]*\s*([A-Z0-9-]+)',  # 编号: NC50F
                    r'(型号|编号)([A-Z0-9-]+)',           # 编号NC50F
                    r'(型号|编号):([A-Z0-9-]+)',          # 编号:NC50F
                    r'\b([A-Z0-9-]+)\b',                 # 纯字母数字型号
                ]
                
                for pattern in model_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        try:
                            if len(match.groups()) == 2:
                                model_number = match.group(2)
                            else:
                                model_number = match.group(1)
                            break
                        except (IndexError, ValueError):
                            continue
                
                # 2. 如果当前文本中没有，尝试从整个原始订单文本中提取
                if not model_number and original_text:
                    for pattern in model_patterns:
                        match = re.search(pattern, original_text, re.IGNORECASE)
                        if match:
                            try:
                                if len(match.groups()) == 2:
                                    model_number = match.group(2)
                                else:
                                    model_number = match.group(1)
                                break
                            except (IndexError, ValueError):
                                continue
                
                product["model_number"] = model_number
                
                # 使用提取的单价和规格
                product["unit_price"] = unit_price
                product["quantity_kg"] = quantity_info["kg"]
                product["quantity_tins"] = quantity_info["tins"]
                product["tin_spec"] = tin_spec
            else:
                # 非自定义模式，必须从数据库匹配到产品
                # 如果数据库中没有匹配到产品，返回None
                logger.info(f"非自定义模式下，数据库中未匹配到产品: {text}")
                return None
            
            # 确保数量信息正确
            if product["quantity_tins"] > 0:
                # 如果有桶数，计算公斤数
                if product["tin_spec"] > 0:
                    product["quantity_kg"] = round(product["quantity_tins"] * product["tin_spec"], 1)
            elif product["quantity_kg"] > 0:
                # 如果有公斤数，计算桶数
                if product["tin_spec"] > 0:
                    product["quantity_tins"] = max(1, int(round(product["quantity_kg"] / product["tin_spec"], 0)))
            
            # 计算金额
            if product["unit_price"] > 0 and product["quantity_kg"] > 0:
                product["amount"] = round(product["unit_price"] * product["quantity_kg"], 2)
            
            # 自定义模式下，只要产品名称和数量有效就返回
            if is_custom:
                if product["name"] and (product["quantity_kg"] > 0 or product["quantity_tins"] > 0):
                    return product
            else:
                # 非自定义模式，需要更严格的验证
                if product["name"] and (product["quantity_kg"] > 0 or product["quantity_tins"] > 0):
                    return product
            
            return None
            
        except Exception as e:
            logger.error(f"解析单个产品失败: {e}")
            return None
    
    def _extract_purchase_unit(self, text: str) -> str:
        """提取购买单位"""
        # 合并已知单位和数据库中的单位
        all_units = set(self.KNOWN_PURCHASE_UNITS) | set(self._purchase_units.keys())
        
        # 按名称长度降序排列，优先匹配更长的名称
        sorted_units = sorted(all_units, key=len, reverse=True)
        
        # 特殊处理：蕊芯1 -> 蕊芯家私1（优先处理）
        if "蕊芯1" in text:
            return "蕊芯家私1"
        
        # 特殊处理：蕊芯 -> 蕊芯家私
        if "蕊芯" in text and "蕊芯家私" not in text:
            return "蕊芯家私"
        
        # 然后尝试精确匹配
        for unit in sorted_units:
            if unit in text:
                return unit
        
        return ""
    
    def _extract_product_info(self, text: str, exclude_unit: str) -> Dict[str, str]:
        """提取产品信息"""
        result = {"name": "", "model": ""}
        
        # 移除购买单位
        working_text = text
        if exclude_unit:
            working_text = working_text.replace(exclude_unit, "").strip()
        
        # 移除数量信息
        working_text = self._remove_quantity_info(working_text)
        
        # 清理文本
        working_text = re.sub(r'\s+', ' ', working_text).strip()
        
        # 移除常见前缀
        prefixes = ["要", "买", "订购", "发", "送", "需要"]
        for prefix in prefixes:
            if working_text.startswith(prefix):
                working_text = working_text[len(prefix):].strip()
        
        if working_text:
            result["name"] = working_text
        
        return result
    
    def _remove_quantity_info(self, text: str) -> str:
        """移除数量信息"""
        # 移除 "XX公斤" 或 "XXkg" 等
        text = re.sub(r'\d+(?:\.\d+)?\s*(?:公斤|kg|千克|KG|K)\s*桶?', '', text, flags=re.IGNORECASE)
        
        # 移除 "X桶"
        text = re.sub(r'\d+\s*桶', '', text)
        
        # 移除 "规格XX"
        text = re.sub(r'规格\d+(?:\.\d+)?', '', text)
        
        # 移除 "单价XX"
        text = re.sub(r'单价\d+(?:\.\d+)?', '', text)
        
        return text.strip()
    
    def _extract_quantity(self, text: str) -> Dict[str, float]:
        """提取数量信息"""
        result = {
            "kg": 0.0,
            "tins": 0,
            "tin_spec": 0.0
        }
        
        # 0. 首先检查是否有 "XXkgYY桶" 格式（kg在前，桶在后）
        kg_tins_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|k g|千克|公斤|KG|K)\s*(\d+)\s*桶'
        match = re.search(kg_tins_pattern, text, re.IGNORECASE)
        if match:
            kg = float(match.group(1))
            tins = int(match.group(2))
            if kg > 0 and tins > 0:
                result["kg"] = kg
                result["tins"] = tins
                result["tin_spec"] = round(kg / tins, 1)
                return result
        
        # 1. 首先尝试提取桶数和规格
        tins_pattern = r'(\d+)\s*桶'
        match = re.search(tins_pattern, text)
        if match:
            result["tins"] = int(match.group(1))
            tin_spec = self._extract_tin_spec(text)
            if tin_spec > 0:
                result["tin_spec"] = tin_spec
                result["kg"] = round(result["tins"] * tin_spec, 1)
            else:
                result["tin_spec"] = 10.0
                result["kg"] = result["tins"] * 10.0
            return result
        
        # 2. 提取公斤数 - 只匹配后面跟着单位的数字
        kg_pattern = r'(\d+(?:\.\d+)?)\s*(?:kg|k g|千克|公斤|KG|K)'
        match = re.search(kg_pattern, text, re.IGNORECASE)
        if match:
            kg = float(match.group(1))
            if 0 < kg < 10000:
                result["kg"] = kg
                
                tin_spec = self._extract_tin_spec(text)
                if tin_spec > 0:
                    result["tin_spec"] = tin_spec
                    result["tins"] = max(1, int(round(result["kg"] / tin_spec, 0)))
                else:
                    result["tin_spec"] = 10.0
                    result["tins"] = max(1, int(round(result["kg"] / 10, 0)))
                
                return result
        
        return result
    
    def _extract_tin_spec(self, text: str) -> float:
        """提取桶规格"""
        # 模式0: "规格25" 或 "规格25kg"
        pattern0 = r'规格(\d+(?:\.\d+)?)'
        match = re.search(pattern0, text)
        if match:
            spec = float(match.group(1))
            if spec > 0:
                return spec
        
        # 模式1: "10公斤/桶" 或 "10kg桶"
        pattern1 = r'(\d+(?:\.\d+)?)\s*(?:公斤|kg|KG)\s*[/]?\s*桶'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            spec = float(match.group(1))
            if spec > 0:
                return spec
        
        # 模式2: "桶装10kg"
        pattern2 = r'桶装\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:kg|KG|公斤)'
        match = re.search(pattern2, text, re.IGNORECASE)
        if match:
            spec = float(match.group(1))
            if spec > 0:
                return spec
        
        # 模式3: "每桶10kg"
        pattern3 = r'每\s*桶\s*(\d+(?:\.\d+)?)\s*(?:kg|KG|公斤)'
        match = re.search(pattern3, text, re.IGNORECASE)
        if match:
            spec = float(match.group(1))
            if spec > 0:
                return spec
        
        # 模式4: 常见规格提示词
        spec_keywords = {
            "小桶": 1.0,
            "中桶": 5.0,
            "大桶": 10.0,
            "标准桶": 10.0,
            "常规桶": 10.0,
        }
        
        for keyword, spec in spec_keywords.items():
            if keyword in text:
                return spec
        
        return 0.0
    
    def _load_purchase_units_from_db(self) -> Dict[str, Dict]:
        """从数据库加载购买单位"""
        units = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 尝试查询purchase_units表（新数据库结构）
            cursor.execute("SELECT id, unit_name, contact_person, contact_phone, address FROM purchase_units WHERE is_active = 1")
            
            for row in cursor.fetchall():
                unit_name = row[1]
                units[unit_name] = {
                    "id": row[0],
                    "name": unit_name,
                    "contact_person": row[2] or "",
                    "contact_phone": row[3] or "",
                    "address": row[4] or ""
                }
            
            conn.close()
            
            logger.info(f"成功加载 {len(units)} 个购买单位信息")
            for unit_name, unit_info in units.items():
                logger.debug(f"  - {unit_name}: 联系人={unit_info['contact_person']}, 电话={unit_info['contact_phone']}")
            
        except Exception as e:
            logger.error(f"加载购买单位失败: {e}")
            # 如果purchase_units表不存在，返回空字典，但不影响解析功能
            units = {}
        
        return units
    
    def _match_product_from_db(self, text: str, unit_name: str = None, number_mode: bool = False) -> Optional[Dict]:
        """从数据库匹配产品 - 支持模糊匹配和客户关联"""
        try:
            # 确定使用哪个数据库文件
            db_path = self.db_path
            if unit_name:
                # 构建单位数据库文件路径
                unit_db_name = f"{unit_name}.db"
                unit_db_path = os.path.join(self.unit_database_dir, unit_db_name)
                # 检查单位数据库是否存在
                if os.path.exists(unit_db_path):
                    db_path = unit_db_path
                    logger.info(f"使用购买单位专属数据库: {unit_db_path}")
                else:
                    logger.info(f"未找到购买单位 {unit_name} 的专属数据库，使用默认数据库: {self.db_path}")
            else:
                logger.info("未提供购买单位名称，使用默认数据库")
            
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 清理输入文本，移除数量信息
            search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', text)
            # 编号模式下保留数字
            if not number_mode:
                search_text = re.sub(r'\d+(?:\.\d+)?', '', search_text)
            # 移除购买单位名称（如果存在）
            if unit_name:
                search_text = search_text.replace(unit_name, '').strip()
            
            # 提取产品关键词
            product_keywords = self._extract_product_keywords(search_text)
            
            # 处理关键词，尝试从每个关键词中提取型号
            processed_keywords = []
            for keyword in product_keywords:
                # 修复：使用更宽松的正则表达式，支持连字符和星号
                # 优先匹配包含连字符或星号的完整型号（如24-4-8*, 9806A等）
                model_match = re.search(r'[A-Z0-9\-*]+', keyword, re.IGNORECASE)
                if model_match:
                    # 确保匹配到的内容不是太短
                    matched_text = model_match.group(0)
                    if len(matched_text) >= 2:
                        processed_keywords.append(matched_text)
                    else:
                        # 如果匹配太短，保留原始关键词
                        processed_keywords.append(keyword)
                else:
                    # 保留原始关键词
                    processed_keywords.append(keyword)
            
            # 如果没有关键词，尝试直接从文本中提取型号
            if not processed_keywords:
                # 尝试提取型号（数字+字母组合）
                model_match = re.search(r'\b[A-Z0-9]+\b', search_text, re.IGNORECASE)
                if model_match:
                    processed_keywords = [model_match.group(0)]
                else:
                    # 尝试提取纯数字型号（但排除单个数字）
                    number_match = re.search(r'\b\d{2,}\b', search_text)
                    if number_match:
                        processed_keywords = [number_match.group(0)]
            
            # 使用处理后的关键词
            product_keywords = processed_keywords
            
            if not product_keywords:
                conn.close()
                return None
            
            logger.info(f"产品关键词: {product_keywords}")
            
            # 使用新的数据库结构
            try:
                # 优先根据购买单位匹配专属产品
                if unit_name:
                    logger.info(f"根据购买单位 {unit_name} 匹配专属产品")
                    
                    # 先获取购买单位的ID
                    unit_id = None
                    try:
                        cursor.execute('''
                            SELECT id FROM purchase_units WHERE unit_name = ?
                        ''', [unit_name])
                        unit_row = cursor.fetchone()
                        if unit_row:
                            unit_id = unit_row[0]
                            logger.info(f"找到购买单位ID: {unit_id}")
                    except Exception as e:
                        # 专属数据库可能没有 purchase_units 表，这是正常的
                        if "no such table" in str(e):
                            logger.debug(f"购买单位 {unit_name} 专属数据库中没有 purchase_units 表，跳过客户关联匹配")
                        else:
                            logger.debug(f"获取购买单位ID失败: {e}")
                        unit_id = None  # 确保设置为None
                    
                    # 如果找到购买单位ID，优先匹配该客户的专属产品
                    if unit_id is not None:  # 明确检查是否为None
                        for keyword in product_keywords:
                            if len(keyword) >= 2:
                                # 编号模式下优先匹配产品型号（不区分大小写）
                                if number_mode:
                                    # 尝试匹配该客户的专属产品（通过型号，不区分大小写）
                                    cursor.execute('''
                                        SELECT p.model_number, p.name, p.specification, cp.custom_price
                                        FROM products p
                                        JOIN customer_products cp ON p.id = cp.product_id
                                        WHERE cp.unit_id = ? AND UPPER(p.model_number) = UPPER(?) AND cp.is_active = 1
                                        LIMIT 1
                                    ''', [unit_id, keyword])
                                    row = cursor.fetchone()
                                    if row:
                                        conn.close()
                                        logger.info(f"成功匹配购买单位专属产品(通过编号): {row[1]}, 型号: {row[0]}")
                                        return {
                                            "model_number": row[0],
                                            "name": row[1],
                                            "specification": row[2] or "",
                                            "price": float(row[3]) if row[3] else 0.0
                                        }
                                    
                                    # 模糊匹配（不区分大小写）
                                    cursor.execute('''
                                        SELECT p.model_number, p.name, p.specification, cp.custom_price
                                        FROM products p
                                        JOIN customer_products cp ON p.id = cp.product_id
                                        WHERE cp.unit_id = ? AND UPPER(p.model_number) LIKE UPPER(?) AND cp.is_active = 1
                                        LIMIT 1
                                    ''', [unit_id, f'%{keyword}%'])
                                    row = cursor.fetchone()
                                    if row:
                                        conn.close()
                                        logger.info(f"成功匹配购买单位专属产品(通过编号模糊匹配): {row[1]}, 型号: {row[0]}")
                                        return {
                                            "model_number": row[0],
                                            "name": row[1],
                                            "specification": row[2] or "",
                                            "price": float(row[3]) if row[3] else 0.0
                                        }
                                
                                # 尝试匹配该客户的专属产品（通过名称）
                                cursor.execute('''
                                    SELECT p.model_number, p.name, p.specification, cp.custom_price
                                     FROM products p
                                     JOIN customer_products cp ON p.id = cp.product_id
                                     WHERE cp.unit_id = ? AND p.name LIKE ? AND cp.is_active = 1
                                    LIMIT 1
                                ''', [unit_id, f'%{keyword}%'])
                                row = cursor.fetchone()
                                if row:
                                    conn.close()
                                    logger.info(f"成功匹配购买单位专属产品(通过名称): {row[1]}, 型号: {row[0]}")
                                    return {
                                        "model_number": row[0],
                                        "name": row[1],
                                        "specification": row[2] or "",
                                        "price": float(row[3]) if row[3] else 0.0
                                    }
        
                # 编号模式下优先匹配产品型号
                if number_mode:
                    logger.info("启用编号模式，优先匹配产品型号")
                    
                    # 分离字母数字组合关键词和纯数字关键词
                    alpha_numeric_keywords = []
                    numeric_keywords = []
                    
                    for keyword in product_keywords:
                        if re.match(r'^[A-Z0-9]+$', keyword, re.IGNORECASE):
                            # 字母数字组合，可能是型号
                            alpha_numeric_keywords.append(keyword)
                        elif keyword.isdigit():
                            # 纯数字
                            numeric_keywords.append(keyword)
                        else:
                            # 其他关键词
                            alpha_numeric_keywords.append(keyword)
                    
                    logger.info(f"字母数字关键词: {alpha_numeric_keywords}")
                    logger.info(f"纯数字关键词: {numeric_keywords}")
                    
                    # 优先级1: 精确匹配型号（不区分大小写），优先使用字母数字组合关键词
                    for keyword in alpha_numeric_keywords:
                        cursor.execute('''
                            SELECT p.model_number, p.name, p.specification, p.price
                            FROM products p
                            WHERE UPPER(p.model_number) = UPPER(?)
                            LIMIT 1
                        ''', [keyword])
                        row = cursor.fetchone()
                        if row:
                            conn.close()
                            logger.info(f"成功匹配产品(通过编号): {row[1]}, 型号: {row[0]}")
                            return {
                                "model_number": row[0],
                                "name": row[1],
                                "specification": row[2] or "",
                                "price": float(row[3]) if row[3] else 0.0
                            }
                    
                    # 优先级2: 模糊匹配型号（不区分大小写），优先使用字母数字组合关键词
                    for keyword in alpha_numeric_keywords:
                        if len(keyword) >= 2:
                            cursor.execute('''
                                SELECT p.model_number, p.name, p.specification, p.price
                                FROM products p
                                WHERE UPPER(p.model_number) LIKE UPPER(?)
                                LIMIT 1
                            ''', [f'%{keyword}%'])
                            row = cursor.fetchone()
                            if row:
                                conn.close()
                                logger.info(f"成功匹配产品(通过编号模糊匹配): {row[1]}, 型号: {row[0]}")
                                return {
                                    "model_number": row[0],
                                    "name": row[1],
                                    "specification": row[2] or "",
                                    "price": float(row[3]) if row[3] else 0.0
                                }
                    
                    # 优先级3: 纯数字关键词容错匹配（支持9083→9803等近似匹配）
                    for keyword in numeric_keywords:
                        if len(keyword) >= 2:
                            # 先尝试精确匹配
                            cursor.execute('''
                                SELECT p.model_number, p.name, p.specification, p.price
                                FROM products p
                                WHERE UPPER(p.model_number) = UPPER(?)
                                LIMIT 1
                            ''', [keyword])
                            row = cursor.fetchone()
                            if row:
                                conn.close()
                                logger.info(f"成功匹配产品(通过数字编号): {row[1]}, 型号: {row[0]}")
                                return {
                                    "model_number": row[0],
                                    "name": row[1],
                                    "specification": row[2] or "",
                                    "price": float(row[3]) if row[3] else 0.0
                                }
                            
                            # 尝试容错匹配：例如9083→9803
                            # 特殊处理常见的手误输入
                            rows = []
                            if keyword in ['9083', '9830', '9838']:  # 常见手误
                                # 尝试98开头的型号
                                cursor.execute('''
                                    SELECT p.model_number, p.name, p.specification, p.price
                                    FROM products p
                                    WHERE UPPER(p.model_number) LIKE '98%'
                                    ORDER BY p.model_number
                                    LIMIT 3
                                ''')
                                rows = cursor.fetchall()
                            else:
                                cursor.execute('''
                                    SELECT p.model_number, p.name, p.specification, p.price
                                    FROM products p
                                    WHERE (UPPER(p.model_number) LIKE UPPER(?) OR UPPER(p.model_number) LIKE UPPER(?))
                                    ORDER BY p.model_number
                                    LIMIT 3
                                ''', [f'{keyword[0:2]}%', f'{keyword[0:3]}%'])
                                rows = cursor.fetchall()
                            
                            if rows:
                                # 选择最相似的结果
                                best_match = rows[0]
                                conn.close()
                                logger.info(f"容错匹配产品(数字编号): {best_match[1]}, 型号: {best_match[0]}, 原始关键词: {keyword}")
                                return {
                                    "model_number": best_match[0],
                                    "name": best_match[1],
                                    "specification": best_match[2] or "",
                                    "price": float(best_match[3]) if best_match[3] else 0.0
                                }
                    
                    # 编号模式下型号匹配失败后，尝试名称匹配
                    logger.info("编号模式下型号匹配失败，尝试名称匹配")
                
                # 正常模式：优先匹配产品名称
                # 优先级1: 精确匹配产品名称
                for keyword in product_keywords:
                    if len(keyword) >= 2:
                        cursor.execute('''
                            SELECT p.model_number, p.name, p.specification, p.price
                            FROM products p
                            WHERE p.name = ?
                            LIMIT 1
                        ''', [keyword])
                        row = cursor.fetchone()
                        if row:
                            conn.close()
                            logger.info(f"成功匹配产品(通过名称): {row[1]}, 型号: {row[0]}")
                            return {
                                "model_number": row[0],
                                "name": row[1],
                                "specification": row[2] or "",
                                "price": float(row[3]) if row[3] else 0.0
                            }
                
                # 优先级2: 模糊匹配产品名称（扩展逻辑支持PE相关产品的匹配）
                for keyword in product_keywords:
                    if len(keyword) >= 2:
                        # 特殊处理：白底稀释剂 -> PE白底漆稀释剂
                        if "稀释剂" in keyword and "白底" in keyword:
                            cursor.execute('''
                                SELECT p.model_number, p.name, p.specification, p.price
                                FROM products p
                                WHERE p.name LIKE '%白底漆稀释剂%'
                                LIMIT 1
                            ''')
                            row = cursor.fetchone()
                            if row:
                                conn.close()
                                logger.info(f"成功匹配产品(扩展名称匹配): {row[1]}, 型号: {row[0]}")
                                return {
                                    "model_number": row[0],
                                    "name": row[1],
                                    "specification": row[2] or "",
                                    "price": float(row[3]) if row[3] else 0.0
                                }
                        
                        # 正常的模糊匹配
                        cursor.execute('''
                            SELECT p.model_number, p.name, p.specification, p.price
                            FROM products p
                            WHERE p.name LIKE ?
                            LIMIT 1
                        ''', [f'%{keyword}%'])
                        row = cursor.fetchone()
                        if row:
                            conn.close()
                            logger.info(f"成功匹配产品(通过名称): {row[1]}, 型号: {row[0]}")
                            return {
                                "model_number": row[0],
                                "name": row[1],
                                "specification": row[2] or "",
                                "price": float(row[3]) if row[3] else 0.0
                            }
                
                # 优先级3: 精确匹配型号（不区分大小写）
                for keyword in product_keywords:
                    cursor.execute('''
                        SELECT p.model_number, p.name, p.specification, p.price
                        FROM products p
                        WHERE UPPER(p.model_number) = UPPER(?)
                        LIMIT 1
                    ''', [keyword])
                    row = cursor.fetchone()
                    if row:
                        conn.close()
                        logger.info(f"成功匹配产品(通过型号): {row[1]}, 型号: {row[0]}")
                        return {
                            "model_number": row[0],
                            "name": row[1],
                            "specification": row[2] or "",
                            "price": float(row[3]) if row[3] else 0.0
                        }
                
                # 优先级4: 模糊匹配型号（不区分大小写）
                for keyword in product_keywords:
                    if len(keyword) >= 2:
                        cursor.execute('''
                            SELECT p.model_number, p.name, p.specification, p.price
                            FROM products p
                            WHERE UPPER(p.model_number) LIKE UPPER(?)
                            LIMIT 1
                        ''', [f'%{keyword}%'])
                        row = cursor.fetchone()
                        if row:
                            conn.close()
                            logger.info(f"成功匹配产品(通过型号): {row[1]}, 型号: {row[0]}")
                            return {
                                "model_number": row[0],
                                "name": row[1],
                                "specification": row[2] or "",
                                "price": float(row[3]) if row[3] else 0.0
                            }
                
                # 优先级5: 智能模糊匹配（处理P白底、P白底漆等简化输入）
                logger.info(f"尝试智能模糊匹配，关键词: {product_keywords}")
                fuzzy_match = self._fuzzy_match_products(cursor, product_keywords, [1.0, unit_id] if unit_id else None)
                if fuzzy_match:
                    conn.close()
                    logger.info(f"成功匹配产品(通过智能模糊匹配): {fuzzy_match['name']}, 型号: {fuzzy_match['model_number']}")
                    return fuzzy_match
            except Exception as e:
                logger.error(f"产品匹配异常: {e}")
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"匹配产品失败: {e}")
            return None
    
    def _row_to_product_with_price(self, row) -> Dict:
        """将数据库行转换为产品字典（包含自定义价格）"""
        # 确保价格为float类型，避免None值
        price = 0.0
        try:
            price = float(row[4]) if row[4] is not None else 0.0
        except (TypeError, ValueError):
            price = 0.0
        
        return {
            "model_number": row[0],
            "name": row[1],
            "specification": row[2] or "",
            "price": price  # final_price
        }
    
    def _extract_product_keywords(self, text: str) -> List[str]:
        """提取产品关键词"""
        keywords = []
        
        # 移除常见产品类型前缀（如PU、PE、NC等）
        text = re.sub(r'^(?:PU|PE|NC|PV|AC)\s*', '', text, flags=re.IGNORECASE)
        
        # 产品关键词列表
        product_indicators = ["漆", "剂", "胶", "水", "油", "粉", "膏", "稀释剂", "固化剂", "底漆", "面漆", "白底", "白底漆", "色浆", "树脂", "助剂", "哑光", "亮光", "三分光", "全哑"]
        
        for indicator in product_indicators:
            if indicator in text:
                pattern = rf'[^\s]*?{re.escape(indicator)}[^\s]*'
                matches = re.findall(pattern, text)
                keywords.extend(matches)
        
        # 尝试从文本中提取型号（无论是否找到产品关键词）
        # 修复：支持连字符和星号的型号提取
        model_matches = re.findall(r'[A-Z0-9\-*]+', text, re.IGNORECASE)
        if model_matches:
            # 过滤掉太短的匹配（如单个数字或字母）
            valid_models = [m for m in model_matches if len(m) >= 2]
            keywords.extend(valid_models)
        else:
            # 尝试提取纯数字型号（但排除单个数字）
            number_matches = re.findall(r'\d{2,}', text)
            if number_matches:
                keywords.extend(number_matches)
        
        # 如果仍然没有关键词，返回整个文本
        if not keywords:
            keywords = [text]
        
        # 去重并清理
        keywords = list(set(keywords))
        keywords = [k.strip() for k in keywords if k.strip()]
        
        return keywords
    
    def _fuzzy_match_products(self, cursor, keywords: List[str], base_params: List = None) -> Optional[Dict]:
        """模糊匹配产品"""
        try:
            if base_params and len(base_params) >= 2:
                cursor.execute('''
                    SELECT p.model_number, p.name, p.specification, p.price, COALESCE(cp.custom_price, p.price * ?) as final_price
                    FROM products p
                    LEFT JOIN customer_products cp ON p.id = cp.product_id AND cp.unit_id = ? AND cp.is_active = 1
                    WHERE p.is_active = 1
                ''', base_params[:2])
            else:
                cursor.execute('SELECT model_number, name, specification, price, price as final_price FROM products p WHERE is_active = 1')
            
            all_products = cursor.fetchall()
            
            best_score = 0
            best_product = None
            
            for row in all_products:
                product_name = row[1] or ""
                product_model = row[0] or ""
                
                score = 0
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    name_lower = product_name.lower()
                    model_lower = product_model.lower()
                    
                    if keyword_lower in name_lower:
                        score += 10
                    if keyword_lower in model_lower:
                        score += 5
                    
                    if len(keyword) >= 3:
                        if keyword_lower in name_lower or keyword_lower in model_lower:
                            score += 5
                
                if score > best_score:
                    best_score = score
                    best_product = row
            
            if best_score >= 5 and best_product:
                return self._row_to_product_with_price(best_product)
            
            return None
            
        except Exception as e:
            logger.error(f"模糊匹配失败: {e}")
            return None
    
    def _row_to_product(self, row) -> Dict:
        """将数据库行转换为产品字典"""
        return {
            "model_number": row[0],
            "name": row[1],
            "specification": row[2] or "",
            "price": float(row[3]) if row[3] else 0.0
        }
    
    def calculate_tins_from_kg(self, kg: float, tin_spec: float = None) -> Tuple[int, float]:
        """
        根据公斤数计算桶数
        
        Args:
            kg: 总公斤数
            tin_spec: 桶规格（kg/桶），如果不指定则自动推断
            
        Returns:
            (桶数, 使用的桶规格)
        """
        if tin_spec and tin_spec > 0:
            tins = int(round(kg / tin_spec, 0))
            return max(1, tins), tin_spec
        
        # 自动推断最合适的桶规格
        for spec in sorted(self.COMMON_TIN_SPECS, reverse=True):
            if kg >= spec:
                tins = max(1, int(round(kg / spec, 0)))
                return tins, spec
        
        # 默认使用10kg桶
        return max(1, int(round(kg / 10, 0))), 10.0


class ShipmentRecordManager:
    """发货记录管理器"""
    
    def __init__(self, db_path: str = None):
        """初始化"""
        if db_path is None:
            self.db_path = 'products.db'
        else:
            self.db_path = db_path
    
    def create_record(self, order: ParsedOrder, unit_id: int = None) -> int:
        """
        创建发货记录（支持多产品）
        
        Returns:
            最后一个记录的ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shipment_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    purchase_unit TEXT NOT NULL,
                    unit_id INTEGER,
                    product_name TEXT NOT NULL,
                    model_number TEXT,
                    quantity_kg REAL NOT NULL,
                    quantity_tins INTEGER NOT NULL,
                    tin_spec REAL,
                    unit_price REAL DEFAULT 0,
                    amount REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_text TEXT,
                    parsed_data TEXT
                )
            ''')
            
            # 为每个产品创建单独的记录
            record_ids = []
            
            # 如果有 products 列表，为每个产品创建记录
            if order.products:
                for product in order.products:
                    cursor.execute('''
                        INSERT INTO shipment_records (
                            purchase_unit, unit_id, product_name, model_number,
                            quantity_kg, quantity_tins, tin_spec, unit_price, amount,
                            raw_text, parsed_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        order.purchase_unit,
                        unit_id,
                        product.get('name', ''),
                        product.get('model_number', ''),
                        product.get('quantity_kg', 0),
                        product.get('quantity_tins', 0),
                        product.get('tin_spec', 10.0),
                        product.get('unit_price', 0),
                        product.get('amount', 0),
                        order.raw_text,
                        str(order.parsed_data)
                    ))
                    record_ids.append(cursor.lastrowid)
            else:
                # 兼容旧格式：单个产品
                cursor.execute('''
                    INSERT INTO shipment_records (
                        purchase_unit, unit_id, product_name, model_number,
                        quantity_kg, quantity_tins, tin_spec, unit_price, amount,
                        raw_text, parsed_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order.purchase_unit,
                    unit_id,
                    order.product_name,
                    order.model_number,
                    order.quantity_kg,
                    order.quantity_tins,
                    order.tin_spec,
                    order.unit_price,
                    order.amount,
                    order.raw_text,
                    str(order.parsed_data)
                ))
                record_ids.append(cursor.lastrowid)
            
            conn.commit()
            conn.close()
            
            logger.info(f"创建发货记录成功: IDs={record_ids}")
            return record_ids[-1] if record_ids else None
            
        except Exception as e:
            logger.error(f"创建发货记录失败: {e}")
            raise
    
    def get_record(self, record_id: int) -> Optional[Dict]:
        """获取发货记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM shipment_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                columns = ['id', 'purchase_unit', 'unit_id', 'product_name', 'model_number',
                          'quantity_kg', 'quantity_tins', 'tin_spec', 'unit_price', 'amount',
                          'status', 'created_at', 'updated_at', 'raw_text', 'parsed_data']
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"获取发货记录失败: {e}")
            return None
    
    def update_status(self, record_id: int, status: str) -> bool:
        """更新记录状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE shipment_records
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, record_id))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"更新状态失败: {e}")
            return False
    
    def get_pending_records(self) -> List[Dict]:
        """获取待处理记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM shipment_records
                WHERE status = 'pending'
                ORDER BY created_at DESC
            ''')
            
            columns = ['id', 'purchase_unit', 'unit_id', 'product_name', 'model_number',
                      'quantity_kg', 'quantity_tins', 'tin_spec', 'unit_price', 'amount',
                      'status', 'created_at', 'updated_at', 'raw_text', 'parsed_data']
            
            records = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            
            return records
            
        except Exception as e:
            logger.error(f"获取待处理记录失败: {e}")
            return []


# 便捷函数
def parse_shipment_order(text: str, db_path: str = None) -> ParsedOrder:
    """解析发货订单"""
    parser = ShipmentParser(db_path)
    return parser.parse(text)


def create_shipment_record(order: ParsedOrder, db_path: str = None) -> int:
    """创建发货记录"""
    manager = ShipmentRecordManager(db_path)
    return manager.create_record(order)


if __name__ == '__main__':
    # 测试解析器
    parser = ShipmentParser()
    
    test_cases = [
        "蕊芯PU哑光黑面漆20公斤",
        "蕊芯 PU净味面漆稀释剂 180KG 桶装20kg",
        "蕊芯 A1(553) PU净味哑光浅蓝色漆 26KG",
        "七彩乐园 9803 PE白底漆 28KG",
    ]
    
    print("=== 发货单解析测试 ===\n")
    
    for text in test_cases:
        print(f"输入: {text}")
        result = parser.parse(text)
        print(f"购买单位: {result.purchase_unit}")
        print(f"产品名称: {result.product_name}")
        print(f"产品型号: {result.model_number}")
        print(f"数量: {result.quantity_kg}kg = {result.quantity_tins}桶 (每桶{result.tin_spec}kg)")
        print(f"单价: {result.unit_price}")
        print(f"金额: {result.amount}")
        print(f"有效: {result.is_valid()}")
        print("-" * 50)