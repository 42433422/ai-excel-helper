#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI增强的发货单解析器
使用DeepSeek AI辅助解析复杂订单格式
"""

import re
import json
import os
import sqlite3
import glob
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from shipment_parser import ShipmentParser, ParsedOrder
from ai_assistant.ai_analyzer import AIAnalyzer
import logging

# 配置日志编码
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)


class AIAugmentedShipmentParser(ShipmentParser):
    """AI增强的发货单解析器"""
    
    def __init__(self, db_path: str = None):
        """初始化"""
        # 使用当前目录中的数据库文件
        if db_path is None:
            # 使用当前目录的products.db
            self.db_path = "products.db"
        else:
            self.db_path = db_path
        
        # 从数据库加载购买单位
        self._purchase_units = self._load_purchase_units_from_db()
        
        # 加载单位数据库映射
        self._unit_databases = self._load_unit_databases()
        
        # 初始化AI分析器
        self.ai_analyzer = AIAnalyzer()
        
    def _load_purchase_units_from_db(self) -> Dict[str, Dict]:
        """从数据库加载购买单位"""
        units = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询purchase_units表
            cursor.execute("SELECT id, unit_name, contact_person, contact_phone, address FROM purchase_units WHERE is_active = 1")
            
            for row in cursor.fetchall():
                unit_name = row[1]
                units[unit_name] = {
                    "id": row[0],
                    "name": unit_name,
                    "contact_person": row[2],
                    "contact_phone": row[3],
                    "address": row[4]
                }
            
            conn.close()
        except Exception as e:
            logger.warning(f"从数据库加载购买单位失败: {e}")
        
        return units
    
    def _load_unit_databases(self) -> Dict[str, str]:
        """加载单位数据库映射"""
        unit_databases = {}
        
        try:
            units_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unit_databases')
            
            if os.path.exists(units_dir):
                db_files = glob.glob(os.path.join(units_dir, '*.db'))
                
                for db_path in db_files:
                    db_filename = os.path.basename(db_path)
                    unit_name = db_filename[:-3]  # 移除 .db 后缀
                    unit_databases[unit_name] = db_path
            
            logger.info(f"加载了 {len(unit_databases)} 个单位数据库映射")
            
        except Exception as e:
            logger.warning(f"加载单位数据库映射失败: {e}")
        
        return unit_databases
    
    def _smart_match_unit(self, input_unit: str) -> Optional[str]:
        """智能匹配客户单位简称到完整名称"""
        if not input_unit:
            return None
            
        input_unit = input_unit.strip()
        
        # 首先尝试精确匹配
        if input_unit in self._unit_databases:
            logger.info(f"精确匹配客户单位: {input_unit}")
            return input_unit
        
        # 智能匹配：查找包含输入的数据库名
        for db_name in self._unit_databases.keys():
            # 检查输入是否完全匹配数据库名的某个部分
            if input_unit in db_name:
                logger.info(f"智能匹配客户单位: {input_unit} -> {db_name}")
                return db_name
        
        # 使用AI进行模糊匹配
        try:
            ai_matched = self._ai_match_unit(input_unit)
            if ai_matched:
                logger.info(f"AI匹配客户单位: {input_unit} -> {ai_matched}")
                return ai_matched
        except Exception as e:
            logger.warning(f"AI匹配失败: {e}")
        
        logger.warning(f"无法匹配客户单位: {input_unit}")
        return None
    
    def _ai_match_unit(self, input_unit: str) -> Optional[str]:
        """使用AI进行客户单位匹配"""
        try:
            # 准备所有可用的单位名称
            available_units = list(self._unit_databases.keys())
            
            prompt = f"""你是客户单位智能匹配助手。

输入的客户简称：{input_unit}

可用单位列表：
{chr(10).join([f"{i+1}. {unit}" for i, unit in enumerate(available_units)])}

任务：请从可用单位列表中找到最匹配的一个单位名称。匹配规则：
1. 优先匹配完全包含输入简称的单位
2. 对于"志泓"类型的输入，匹配"志泓家私"
3. 对于"中江博郡"类型的输入，匹配"中江博郡家私"
4. 如果找不到匹配，返回"无匹配"

请直接返回匹配的完整单位名称，如果没有匹配则返回"无匹配"："""

            # 构建用户消息
            user_message = prompt
            
            # 调用AI API
            api_key = os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.1,
                "max_tokens": 100
            }

            import requests
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    ai_response = result["choices"][0]["message"]["content"].strip()
                    
                    # 检查AI返回的单位是否在可用列表中
                    for unit in available_units:
                        if ai_response == unit:
                            return unit
                    
                    # 如果AI返回了包含关系的匹配，也尝试验证
                    if ai_response != "无匹配" and ai_response in available_units:
                        return ai_response
            
        except Exception as e:
            logger.warning(f"AI客户单位匹配调用失败: {e}")
        
        return None
    
    def _match_product_from_db(self, search_text: str, unit_name: str = None, number_mode: bool = False) -> Optional[Dict]:
        """从单位数据库匹配产品 - 严格限制在指定单位中"""
        print(f"DEBUG: _match_product_from_db 开始 - 搜索文本: '{search_text}', 单位: '{unit_name}', 模式: {number_mode}")
        try:
            # 清理输入文本，移除数量信息
            clean_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', search_text)
            # 编号模式下保留数字
            if not number_mode:
                clean_text = re.sub(r'\d+(?:\.\d+)?', '', clean_text)
            # 移除购买单位名称（如果存在）
            if unit_name:
                clean_text = clean_text.replace(unit_name, '').strip()
            
            print(f"DEBUG: 清理后的文本: '{clean_text}'")
            
            clean_text = clean_text.strip()
            
            if not clean_text:
                return None
            
            # 如果有单位名称，严格从该单位的数据库搜索
            if unit_name and unit_name in self._unit_databases:
                db_path = self._unit_databases[unit_name]
                product = self._search_in_unit_db(clean_text, db_path, number_mode)
                if product:
                    return product
                else:
                    # 如果在指定单位中未找到，返回None而不是回退到其他单位
                    logger.warning(f"在单位 {unit_name} 中未找到产品: {clean_text}")
                    return None
            else:
                logger.warning(f"未找到单位 {unit_name} 的数据库映射")
                return None
            
        except Exception as e:
            logger.error(f"从数据库匹配产品失败: {e}")
            return None
    
    def _search_in_unit_db(self, search_text: str, db_path: str, number_mode: bool = False) -> Optional[Dict]:
        """在指定单位数据库中搜索产品 - 增强模糊匹配"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取所有产品用于智能匹配
            cursor.execute("""
                SELECT id, model_number, name, price, specification, brand, unit
                FROM products
            """)
            all_products = cursor.fetchall()
            conn.close()
            
            if not all_products:
                return None
            
            # 智能匹配算法
            best_match = self._smart_product_match(search_text, all_products, number_mode)
            
            if best_match:
                product = best_match
                return {
                    'id': product[0],
                    'model_number': product[1] or '',
                    'name': product[2] or '',
                    'price': float(product[3]) if product[3] else 0.0,
                    'specification': product[4] or '',
                    'brand': product[5] or '',
                    'unit': product[6] or ''
                }
            
            return None
            
        except Exception as e:
            logger.error(f"搜索单位数据库 {db_path} 失败: {e}")
            return None
    
    def _smart_product_match(self, search_text: str, all_products: List[tuple], number_mode: bool = False) -> Optional[tuple]:
        """智能产品匹配算法"""
        
        # 定义产品类型关键词映射 - 添加复合产品映射
        product_type_mapping = {
            # 基础产品映射
            '稀释剂': ['稀料', '稀释剂', '面漆稀释剂'],
            '白面漆': ['白面漆', '哑光白面漆', '亮光白面漆'],
            '白底漆': ['白底漆', 'PE白底漆'],
            '封固底漆': ['封固底漆', 'PE封固底漆'],
            '清底漆': ['清底漆', 'PE清底漆'],
            '清面漆': ['清面漆', '三分光清面漆', '五分光清面漆'],
            
            # 复合产品映射 - 关键优化点
            '白底漆稀释剂': ['PE白底漆稀释剂', '白底漆稀释剂', 'PE白底漆稀料', 'PE白底稀释剂'],
            '白底稀释剂': ['PE白底漆稀释剂', '白底漆稀释剂', 'PE白底漆稀料'],  # 移除PE白底稀释剂，避免与PE白底漆混淆
            'PU稀释剂': ['PU净味面漆稀释剂', 'PU稀释剂'],
            'PE稀释剂': ['PE稀释剂', 'PE稀料'],
            '银珠漆': ['PU哑光银珠漆', 'PU哑光浅灰银珠漆'],
        }
        
        # 首先尝试精确匹配数据库中确实存在的产品名称
        exact_matches = []
        for product in all_products:
            product_id, model_number, name, price, specification, brand, unit = product
            if name:
                # 精确匹配（忽略大小写）
                if search_text.lower() == name.lower():
                    exact_matches.append((product, 100, len(name)))  # 最高分数
                    logger.debug(f"精确匹配发现: '{search_text}' = '{name}' (分数: 100)")
                # 搜索文本是产品名称的子集（产品名称包含搜索文本）
                elif search_text.lower() in name.lower():
                    exact_matches.append((product, 80, len(name)))
                    logger.debug(f"搜索文本在产品名中: '{search_text}' in '{name}' (分数: 80)")
                # 产品名称是搜索文本的子集（搜索文本包含产品名称）
                elif name.lower() in search_text.lower():
                    exact_matches.append((product, 70, len(name)))
                    logger.debug(f"产品名在搜索词中: '{name}' in '{search_text}' (分数: 70)")
        
        # 如果有精确匹配，返回最佳匹配
        if exact_matches:
            # 自定义排序逻辑：
            # 1. 按分数降序
            # 2. 分数相同时，不含"稀释剂"或"稀料"的产品优先
            # 3. 再次相同时，按名称长度降序
            def custom_sort_key(match):
                product = match[0]
                name = product[2].lower() if product[2] else ""
                score = match[1]
                length = match[2]
                
                # 稀释剂惩罚因子：含稀释剂的产品值为1，不含的为0
                has_diluent = 1 if '稀释剂' in name or '稀料' in name else 0
                
                # 排序元组：(分数, 稀释剂惩罚因子, 长度)
                # 分数越高越好，稀释剂惩罚因子越小越好，长度越长越好
                return (-score, has_diluent, -length)
            
            exact_matches.sort(key=custom_sort_key)
            best_exact_match = exact_matches[0]
            logger.info(f"精确匹配找到: {best_exact_match[0][2]} (分数: {best_exact_match[1]})")
            return best_exact_match[0]
        
        logger.debug(f"未找到精确匹配，开始模糊匹配: '{search_text}'")
        
        # 提取关键特征
        key_features = self._extract_key_features(search_text)
        
        best_score = 0
        best_product = None
        
        for product in all_products:
            product_id, model_number, name, price, specification, brand, unit = product
            score = 0
            
            # 1. 精确型号匹配（编号模式下）
            if number_mode and model_number:
                if search_text.lower() == model_number.lower():
                    score += 100
                elif search_text.lower() in model_number.lower():
                    score += 50
            
            # 2. 名称匹配评分
            if name:
                name_lower = name.lower()
                search_lower = search_text.lower()
                
                # 1. 精确匹配（忽略大小写）
                if search_lower == name_lower:
                    score += 100
                
                # 2. 搜索词在产品名中（正向匹配）
                elif search_lower in name_lower:
                    print(f"DEBUG: 搜索词 '{search_lower}' 在 '{name_lower}' 中")
                    
                    # 计算基础分数
                    base_score = 60
                    
                    # 关键优先级逻辑：纯漆类产品 > 含稀释剂产品
                    has_diluent = '稀释剂' in name_lower or '稀料' in name_lower
                    is_pure_paint = any(core in name_lower for core in ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])
                    
                    # 优先级层次：
                    # 1. 纯漆类产品（不含稀释剂）- 最高优先级
                    # 2. 非漆类产品 - 中等优先级
                    # 3. 含稀释剂的产品 - 最低优先级
                    
                    if is_pure_paint and not has_diluent:
                        # 纯漆类产品最高优先级
                        if name_lower.rstrip().endswith(tuple(['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆'])):
                            score += base_score + 60  # 纯漆类产品最高优先级
                            print(f"DEBUG: 纯漆类产品 (+60), 分数: {score}")
                        else:
                            score += base_score + 50  # 不含稀释剂的漆类产品
                            print(f"DEBUG: 不含稀释剂漆类产品 (+50), 分数: {score}")
                    elif not has_diluent:
                        # 非漆类产品（不含稀释剂）
                        score += base_score + 30
                        print(f"DEBUG: 不含稀释剂产品 (+30), 分数: {score}")
                    else:
                        # 含稀释剂的产品最低优先级
                        score += base_score + 5  # 含稀释剂的产品最低优先级
                        print(f"DEBUG: 含稀释剂产品 (+5), 分数: {score}")
                
                # 3. 产品名在搜索词中（反向匹配）
                elif name_lower in search_lower:
                    score += 40
                    print(f"DEBUG: 产品名在搜索词中 (+40), 分数: {score}")
                
                # 4. 包含匹配（低优先级）
                else:
                    score += 20  # 包含匹配
                    print(f"DEBUG: 包含匹配, 分数: {score}")
                
                # 关键词匹配
                for keyword in key_features:
                    if keyword in name_lower:
                        score += 30
                
                # 产品类型映射匹配 - 优先检查前缀+产品类型组合
                prefix_mapping = {
                    'PE': ['PE'],
                    'PU': ['PU'],
                }
                
                matched_product_type = None
                candidate_matches = []  # 存储所有候选匹配
                
                for mapped_term, product_types in product_type_mapping.items():
                    if mapped_term in search_lower:
                        for product_type in product_types:
                            if product_type in name_lower:
                                # 检查前缀是否匹配
                                search_prefix = None
                                for prefix, prefix_variants in prefix_mapping.items():
                                    if prefix in search_lower:
                                        search_prefix = prefix
                                        break
                                
                                name_prefix = None
                                for prefix, prefix_variants in prefix_mapping.items():
                                    if prefix in name_lower:
                                        name_prefix = prefix
                                        break
                                
                                # 计算匹配分数
                                term_score = 0
                                if search_prefix and name_prefix:
                                    if search_prefix == name_prefix:
                                        term_score = 50
                                        matched_product_type = product_type
                                        logger.debug(f"前缀+产品类型匹配: '{search_text}' ~ '{name}' (前缀: {search_prefix}, 分数: +50)")
                                    else:
                                        # 前缀不匹配，降低分数
                                        term_score = 5
                                        logger.debug(f"前缀不匹配: '{search_text}' (前缀: {search_prefix}) vs '{name}' (前缀: {name_prefix}, 分数: +5)")
                                else:
                                    # 没有前缀，按原逻辑处理
                                    term_score = 40
                                    matched_product_type = product_type
                                
                                # 添加到候选匹配列表，包含类型信息
                                candidate_matches.append({
                                    'score': term_score,
                                    'mapped_term': mapped_term,
                                    'product_type': product_type,
                                    'product': product
                                })
                
                # 优先级处理：漆类产品优先于稀释剂类产品
                if candidate_matches:
                    # 分类候选匹配
                    paint_keywords = ['白底漆', '白面漆', '清底漆', '清面漆', '封固底漆']
                    diluted_keywords = ['稀释剂', '稀料']
                    
                    paint_matches = []
                    diluted_matches = []
                    other_matches = []
                    
                    for match in candidate_matches:
                        mapped_term = match['mapped_term']
                        if any(keyword in mapped_term for keyword in paint_keywords):
                            paint_matches.append(match)
                        elif any(keyword in mapped_term for keyword in diluted_keywords):
                            diluted_matches.append(match)
                        else:
                            other_matches.append(match)
                    
                    # 选择最高分数的候选
                    best_match = None
                    if paint_matches:
                        best_match = max(paint_matches, key=lambda x: x['score'])
                        logger.debug(f"漆类产品优先级: '{search_text}' ~ '{best_match['product'][2]}' (最终分数: +{best_match['score']})")
                    elif diluted_matches:
                        best_match = max(diluted_matches, key=lambda x: x['score'])
                        logger.debug(f"稀释剂类产品: '{search_text}' ~ '{best_match['product'][2]}' (最终分数: +{best_match['score']})")
                    else:
                        best_match = max(other_matches, key=lambda x: x['score'])
                    
                    if best_match:
                        score += best_match['score']
                
                # 品牌/前缀词匹配（仅在前缀不匹配时使用）
                if not matched_product_type:
                    brand_words = ['PU', 'PE', '净味']
                    for brand_word in brand_words:
                        if brand_word in search_lower and brand_word in name_lower:
                            score += 10
            
            # 3. 型号包含搜索词
            if model_number and search_text.lower() in model_number.lower():
                score += 20
            
            # 4. 更新最佳匹配
            if score > best_score:
                best_score = score
                best_product = product
        
        # 只有当分数超过最低阈值时才返回
        return best_product if best_score >= 30 else None
    
    def _extract_key_features(self, search_text: str) -> List[str]:
        """提取搜索文本的关键特征词"""
        # 移除数量和单位信息
        clean_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', search_text)
        clean_text = re.sub(r'\d+(?:\.\d+)?', '', clean_text)
        
        # 提取关键特征词
        key_words = []
        product_keywords = ['稀释', '白底', '白面', '底漆', '面漆', '封固', '清底', '清面', '哑光', '亮光', '三分光', '五分光', '七分光', '全哑']
        
        for keyword in product_keywords:
            if keyword in clean_text:
                key_words.append(keyword)
        
        return key_words
        
    def _get_deepseek_product_extraction_prompt(self, number_mode: bool = False) -> str:
        """获取DeepSeek产品提取提示词"""
        base_prompt = """你是一个专业的订单解析助手，专注于从订单文本中提取准确的产品信息。

重要规则：

1. 客户识别规则：
   - "蕊芯1" 应该识别为 "蕊芯家私1"
   - "蕊芯" (单独) 应该识别为 "蕊芯家私"
   - 避免将数字"1"识别为客户或产品编号

2. 产品型号识别规则（各客户专属）：
   蕊芯家私1的产品型号如下：
   - PE白底漆 → 型号必须是 "9806"
   - PE稀释剂 → 型号必须是 "9806A"
   - 哑光银珠漆 → 型号必须是 "24-4-8*"
   
   博旺家私的产品型号如下：
   - PU哑光米白色漆 → 型号必须是 "250301"
   - PU亮光香槟色漆 → 型号必须是 "305-313"
   - PU哑光帝豪金色漆 → 型号必须是 "25-4-2"
   - PU哑光暗夜绿砂面漆 → 型号必须是 "GC4580-2"
   - PU亮光米白专用固化剂 → 型号必须是 "555"

3. 产品识别规则：
   - 产品编号通常是字母+数字组合（如9806、8520F等）
   - 产品名称通常是描述性文本（如PE白底漆、哑光银珠漆、稀释剂等）
   - 不要将"规格"、"桶"、"KG"等描述性文字识别为产品
   - 不要将"PE"识别为产品型号，PE是产品类型
   - 如果输入中同时包含产品编号和产品名称，将编号填入model_number字段，名称填入name字段

4. 数量识别：
   - "10桶"表示10桶
   - "规格28KG"表示每桶28公斤规格
   - 总重量 = 桶数 × 桶规格

请始终以JSON格式返回分析结果，格式如下：
{
    "purchase_unit": "购买单位名称",
    "products": [
        {
            "name": "产品名称",
            "model_number": "产品型号（必须按照上述规则）",
            "quantity_tins": 桶数,
            "quantity_kg": 公斤数,
            "tin_spec": 每桶规格(kg)
        }
    ]
}

注意事项：
- 不要将"规格"等词语作为产品
- 确保每个产品都有正确的数量信息
- 对于"规格28KG"这样的描述，28KG是桶规格，不是数量
- 桶数和公斤数的关系是：公斤数 = 桶数 × 桶规格
- 如果没有明确给出桶数，根据公斤数和桶规格计算
- 如果没有明确给出公斤数，根据桶数和桶规格计算
- 确保所有数值都是数字类型"""
        
        if number_mode:
            base_prompt += "\n\n特别说明：当前启用了编号模式，请优先识别产品编号，并将其填充到model_number字段中。如果输入文本中包含产品编号，请确保正确识别并提取。"
        
        return base_prompt
    
    def _call_deepseek_for_product_extraction(self, text: str, number_mode: bool = False) -> Optional[Dict]:
        """调用DeepSeek进行产品提取"""
        try:
            # 修改AI分析器的系统提示词为产品提取专用
            original_prompt = self.ai_analyzer.system_prompt
            self.ai_analyzer.system_prompt = self._get_deepseek_product_extraction_prompt(number_mode)
            
            # 构建用户消息
            user_message = f"请从以下订单文本中提取购买单位和产品信息：\n\n{text}"
            
            # 调用AI API
            api_key = os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": self.ai_analyzer.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            }

            import requests
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed_result = json.loads(content)
                
                # 恢复原始提示词
                self.ai_analyzer.system_prompt = original_prompt
                
                # 清理和验证AI返回的结果
                if parsed_result and parsed_result.get("products"):
                    # 确保所有产品数值字段都有正确类型
                    for product in parsed_result["products"]:
                        # 确保数量字段为数值类型
                        # 处理None值
                        tin_value = product.get("quantity_tins")
                        product["quantity_tins"] = int(tin_value) if tin_value is not None else 0
                        
                        kg_value = product.get("quantity_kg")
                        product["quantity_kg"] = float(kg_value) if kg_value is not None else 0.0
                        
                        spec_value = product.get("tin_spec")
                        product["tin_spec"] = float(spec_value) if spec_value is not None else 10.0
                        
                return parsed_result
            else:
                logger.error(f"DeepSeek API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"DeepSeek产品提取失败: {e}")
        
        # 恢复原始提示词
        self.ai_analyzer.system_prompt = original_prompt
        return None
    
    def _split_products(self, text: str, purchase_unit: str) -> List[str]:
        """分割多个产品"""
        # 首先尝试原始分割方法
        products = super()._split_products(text, purchase_unit)
        
        # 检查是否有"规格"被误识别为产品
        has_spec_as_product = any("规格" in p for p in products)
        
        if has_spec_as_product:
            logger.info(f"检测到可能将'规格'误识别为产品，使用AI辅助分割: {text}")
            # 这种情况下，上层的parse方法会直接使用AI解析，所以这里不需要特殊处理
        
        return products
    
    def parse(self, text: str, custom_mode: bool = None, number_mode: bool = False) -> ParsedOrder:
        """解析订单文本"""
        text = text.strip()
        result = ParsedOrder(raw_text=text)
        
        # 只有当custom_mode明确为True时才使用自定义模式
        is_custom = custom_mode if custom_mode is not None else False
        # 编号模式
        is_number_mode = number_mode
        
        try:
            # 1. 先使用传统解析器提取购买单位（更准确）
            traditional_unit = super()._extract_purchase_unit(text)
            logger.info(f"传统解析器提取的购买单位: {traditional_unit}")
            
            # 2. 再尝试使用AI进行产品解析
            ai_result = self._call_deepseek_for_product_extraction(text, number_mode)
            
            if ai_result and ai_result.get("products"):  # AI解析器应该优先使用AI结果
                logger.info("使用AI解析结果")
                
                # 提取购买单位：优先使用传统解析器的结果
                ai_unit = ai_result.get("purchase_unit", "")
                
                # 如果传统解析器提取到了有效的购买单位，优先使用它
                if traditional_unit:
                    result.purchase_unit = traditional_unit
                    logger.info(f"使用传统解析器的购买单位: {traditional_unit} (AI返回: {ai_unit})")
                elif ai_unit:
                    # 如果传统解析器没有提取到购买单位，使用AI的结果
                    matched_unit = self._smart_match_unit(ai_unit)
                    if matched_unit:
                        result.purchase_unit = matched_unit
                        logger.info(f"智能匹配客户单位成功: {ai_unit} -> {matched_unit}")
                    else:
                        result.purchase_unit = ai_unit
                        logger.warning(f"客户单位匹配失败: {ai_unit}")
                else:
                    result.purchase_unit = ""
                
                # 处理AI提取的产品
                all_products = []
                total_kg = 0.0
                total_tins = 0
                total_amount = 0.0
                
                # 使用传统解析器提取产品名称
                traditional_products = super()._split_products(text, traditional_unit) if traditional_unit else []
                logger.info(f"传统解析器提取的产品: {traditional_products}")
                
                # 预处理：清理传统解析的产品名称
                cleaned_products = []
                for trad_product in traditional_products:
                    # 1. 移除数字+单位（桶、kg等）
                    clean_trad = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', trad_product)
                    # 2. 移除规格+数字
                    clean_trad = re.sub(r'规格\d+', '', clean_trad)
                    # 3. 编号模式下保留数字（产品编号），非编号模式下移除剩余的数字
                    if not number_mode:
                        clean_trad = re.sub(r'\d+(?:\.\d+)?', '', clean_trad)
                    # 4. 移除数量词（一桶、两桶等）
                    clean_trad = re.sub(r'(?:一|二|三|四|五|六|七|八|九|十|两|几)\s*桶', '', clean_trad)
                    # 5. 移除多余的空白
                    clean_trad = re.sub(r'\s+', ' ', clean_trad)
                    # 6. 去除首尾空白
                    clean_trad = clean_trad.strip()
                    
                    if clean_trad:
                        cleaned_products.append(clean_trad)
                        print(f"DEBUG: 清理产品: '{trad_product}' -> '{clean_trad}'")
                
                logger.info(f"清理后的产品: {cleaned_products}")
                
                # 处理传统解析分割出的所有产品
                processed_products = {}  # 记录已处理的产品，键为产品名称+型号，值为产品信息
                
                for idx, clean_name in enumerate(cleaned_products):
                    logger.info(f"处理传统解析产品 {idx+1}: '{clean_name}'")
                    
                    # 尝试从数据库获取产品详情
                    db_product = self._match_product_from_db(clean_name, result.purchase_unit, number_mode)
                    
                    if db_product:
                        logger.info(f"传统解析产品匹配成功: {db_product['name']} ({db_product['model_number']})")
                        
                        # 创建产品信息
                        product = {
                            "name": db_product.get("name", clean_name),
                            "model_number": db_product.get("model_number", ""),
                            "quantity_kg": 0.0,
                            "quantity_tins": 0,
                            "tin_spec": 10.0,
                            "unit_price": float(db_product.get("price", 0)) if db_product.get("price") else 0.0,
                            "amount": 0.0,
                            "matched_name": clean_name  # 标记匹配的产品名称，用于去重
                        }
                        
                        # 从原始传统解析产品中提取数量信息
                        print(f"DEBUG: 开始提取数量 - 清理名称: '{clean_name}'")
                        print(f"DEBUG: 原始产品列表: {traditional_products}")
                        
                        quantity_extracted = False
                        for trad_product in traditional_products:
                            print(f"DEBUG: 检查产品: '{trad_product}'")
                            print(f"DEBUG: 包含检查: {clean_name in trad_product}")
                            
                            # 检查原始清理名称是否在原始产品文本中
                            if clean_name in trad_product:
                                print(f"DEBUG: 找到匹配的产品: '{trad_product}'")
                                # 提取数量信息
                                # 提取桶数
                                tin_match = re.search(r'(\d+)桶', trad_product)
                                # 提取规格
                                spec_match = re.search(r'规格(\d+)', trad_product)
                                # 提取kg数（如果有）
                                kg_match = re.search(r'(\d+)kg', trad_product)
                                
                                print(f"DEBUG: 桶数匹配: {tin_match.group(1) if tin_match else '无'}")
                                print(f"DEBUG: 规格匹配: {spec_match.group(1) if spec_match else '无'}")
                                print(f"DEBUG: kg匹配: {kg_match.group(1) if kg_match else '无'}")
                                
                                if tin_match:
                                    product["quantity_tins"] = int(tin_match.group(1))
                                    if spec_match:
                                        product["tin_spec"] = float(spec_match.group(1))
                                    else:
                                        # 如果没有规格，使用默认值
                                        product["tin_spec"] = 10.0
                                    # 计算公斤数
                                    product["quantity_kg"] = product["quantity_tins"] * product["tin_spec"]
                                    print(f"DEBUG: 提取到数量 - 桶数: {product['quantity_tins']}, 规格: {product['tin_spec']}, 公斤: {product['quantity_kg']}")
                                    quantity_extracted = True
                                    break
                                elif kg_match:
                                    # 如果没有桶数但有kg数
                                    product["quantity_kg"] = float(kg_match.group(1))
                                    product["quantity_tins"] = 1  # 默认1桶
                                    product["tin_spec"] = product["quantity_kg"]  # 规格设为kg数
                                    print(f"DEBUG: 提取到kg数: {product['quantity_kg']}kg")
                                    quantity_extracted = True
                                    break
                                else:
                                    print(f"DEBUG: 未找到数量信息")
                        
                        if not quantity_extracted:
                            print(f"DEBUG: 未提取到任何数量信息")
                            # 尝试从整个产品文本中提取数量
                            for trad_product in traditional_products:
                                # 只要包含清理名称的部分，就尝试提取
                                if any(clean_name in part for part in trad_product.split()):
                                    print(f"DEBUG: 尝试从部分匹配提取: '{trad_product}'")
                                    # 提取明确的数量信息，避免提取产品编号中的数字
                                    # 匹配模式：数字+桶，或者中文数字+桶
                                    num_match = re.search(r'(?:\d+|一|二|三|四|五|六|七|八|九|十|两|几)\s*桶', trad_product)
                                    if num_match:
                                        # 提取数字部分
                                        digit_match = re.search(r'\d+', num_match.group(0))
                                        if digit_match:
                                            # 阿拉伯数字
                                            product["quantity_tins"] = int(digit_match.group(1))
                                        else:
                                            # 中文数字转换
                                            chinese_num = re.search(r'[一二三四五六七八十两几]', num_match.group(0))
                                            if chinese_num:
                                                # 简单的中文数字到阿拉伯数字的映射
                                                chinese_to_digit = {
                                                    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                                                    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                                                    '两': 2, '几': 1
                                                }
                                                product["quantity_tins"] = chinese_to_digit.get(chinese_num.group(0), 1)
                                            else:
                                                product["quantity_tins"] = 1
                                        
                                        # 使用规格或默认值计算公斤数
                                        if spec_match:
                                            product["tin_spec"] = float(spec_match.group(1))
                                        else:
                                            product["tin_spec"] = 10.0
                                        product["quantity_kg"] = product["quantity_tins"] * product["tin_spec"]
                                        print(f"DEBUG: 尝试提取到数量: {product['quantity_tins']}桶, 规格: {product['tin_spec']}kg/桶")
                                        break
                        
                        # 计算金额
                        if product["unit_price"] > 0 and product["quantity_kg"] > 0:
                            product["amount"] = round(product["unit_price"] * product["quantity_kg"], 2)
                        
                        # 使用产品名称+型号作为唯一键
                        product_key = f"{product['name']}-{product['model_number']}"
                        processed_products[product_key] = product
                        
                        logger.info(f"已添加产品: {product['name']} x {product['quantity_tins']}桶 ({product['quantity_kg']}kg)")
                    else:
                        logger.warning(f"传统解析产品匹配失败: '{clean_name}'")
                
                # 将处理好的产品添加到最终列表
                for product in processed_products.values():
                    all_products.append(product)
                    total_kg += product["quantity_kg"]
                    total_tins += product["quantity_tins"]
                    total_amount += product["amount"]
                
                # 更新结果
                result.products = all_products
                result.product_name = all_products[0]["name"] if all_products else ""
                result.model_number = all_products[0]["model_number"] if all_products else ""
                result.quantity_kg = total_kg
                result.quantity_tins = total_tins
                result.amount = total_amount
                
                # 保存解析详情
                result.parsed_data = {
                    "purchase_unit": result.purchase_unit,
                    "product_name": result.product_name,
                    "model_number": result.model_number,
                    "quantity_kg": result.quantity_kg,
                    "quantity_tins": result.quantity_tins,
                    "tin_spec": all_products[0]["tin_spec"] if all_products else 0.0,
                    "unit_price": all_products[0]["unit_price"] if all_products else 0.0,
                    "amount": result.amount,
                    "products": all_products,
                    "parse_time": "",
                    "parse_method": "ai",
                    "is_custom": is_custom
                }
                
                return result
            else:
                logger.info("使用传统解析方法")
                # AI解析失败或使用自定义模式，使用传统解析方法
                return super().parse(text, custom_mode, number_mode)
                
        except Exception as e:
            logger.error(f"AI增强解析失败: {e}")
            # 解析失败，使用传统解析方法
            return super().parse(text, custom_mode)
    
    def optimize_voice_recognition(self, voice_text: str) -> str:
        """优化语音识别结果
        
        Args:
            voice_text: 语音识别的原始文本
            
        Returns:
            优化后的文本
        """
        try:
            # 调用DeepSeek AI进行文本优化
            ai_result = self._call_deepseek_for_product_extraction(voice_text, False)
            
            if ai_result:
                # 构建优化后的文本
                optimized_parts = []
                
                # 添加购买单位
                purchase_unit = ai_result.get("purchase_unit", "")
                if purchase_unit:
                    optimized_parts.append(purchase_unit)
                
                # 添加产品信息
                products = ai_result.get("products", [])
                for product in products:
                    name = product.get("name", "")
                    quantity_tins = product.get("quantity_tins", 0)
                    tin_spec = product.get("tin_spec", 0)
                    
                    if name and quantity_tins > 0:
                        product_str = f"{name}{quantity_tins}桶"
                        if tin_spec > 0:
                            product_str += f"，规格{tin_spec}"
                        optimized_parts.append(product_str)
                
                if optimized_parts:
                    return "".join(optimized_parts)
            
            # 如果AI优化失败，返回原始文本
            return voice_text
            
        except Exception as e:
            logger.error(f"优化语音识别结果失败: {e}")
            return voice_text

if __name__ == '__main__':
    # 测试AI增强解析器
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
    
    ai_parser = AIAugmentedShipmentParser()
    
    test_cases = [
        "蕊芯家私:Pe白底漆10桶，规格28KG,24-4-8 哑光银珠:1桶，规格20Kg，PE稀释剂:1桶，规格180KG",
        "七彩乐园PE白底10桶，PE稀释剂180kg1桶，PE哑光白面漆5桶",
        "蕊芯PU哑光黑面漆20公斤",
    ]
    
    print("=== AI增强发货单解析测试 ===\n")
    
    for text in test_cases:
        print(f"输入: {text}")
        result = ai_parser.parse(text)
        print(f"购买单位: {result.purchase_unit}")
        print(f"产品数量: {len(result.products)}")
        for i, product in enumerate(result.products):
            print(f"产品{i+1}: {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}kg, 规格{product['tin_spec']}kg/桶")
        print(f"有效: {result.is_valid()}")
        print("-" * 80)
