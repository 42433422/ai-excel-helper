"""
公司名称模糊匹配工具
- 拼音相似度匹配
- OCR错误纠正
- 模糊字符串匹配
"""

import re
import sqlite3
import os
from typing import Optional, List, Tuple
from difflib import SequenceMatcher

DB_PATH = os.path.join(os.getcwd(), 'products.db')

# 常见OCR识别错误映射
OCR_ERROR_MAP = {
    # 数字与字母混淆
    '0': 'O o',
    'O': '0 o',
    'o': '0 O',
    '1': 'l I i |',
    'l': '1 I i |',
    'I': '1 l i |',
    'i': '1 l I |',
    '|': '1 l I i',
    '5': 'S s',
    'S': '5 s',
    's': '5 S',
    '8': 'B b',
    'B': '8 b',
    'b': '8 B',
    '6': 'G g',
    'G': '6 g',
    'g': '6 G',
    '9': 'g q',
    'q': '9 g',
    # 中文常见混淆
    '瑞': '瑞 玳',
    '幸': '幸 辛',
    '星': '星 晨 芯',
    '晨': '晨 星',
    '芯': '芯 星',
    '玳': '玳 瑞',
    '津': '津 律',
    '律': '律 津',
    '晶': '晶 晨',
    '鑫': '鑫 星',
    '百': '百 白',
    '白': '白 百',
    '华': '华 毕',
    '毕': '毕 华',
    '业': '业 叶',
    '叶': '叶 业',
}

# 常见公司名称关键词
COMMON_KEYWORDS = ['公司', '有限', '责任', '股份', '集团', '厂', '店', '铺', '中心', '企业']


def get_pinyin_first_letter(name: str) -> str:
    """获取公司名称的拼音首字母"""
    try:
        import pypinyin
        pinyin_list = pypinyin.pinyin(name, style=pypinyin.Style.FIRST_LETTER)
        return ''.join([p[0] for p in pinyin_list if p]).upper()
    except:
        return ''


def get_pinyin(name: str) -> str:
    """获取公司名称的完整拼音"""
    try:
        import pypinyin
        pinyin_list = pypinyin.pinyin(name, style=pypinyin.Style.NORMAL)
        return ''.join([p[0] for p in pinyin_list if p])
    except:
        return ''


def get_pinyin_tone(name: str) -> str:
    """获取公司名称的拼音（带声调）"""
    try:
        import pypinyin
        pinyin_list = pypinyin.pinyin(name, style=pypinyin.Style.TONE)
        return ''.join([p[0] for p in pinyin_list if p])
    except:
        return ''


def calculate_similarity(str1: str, str2: str) -> float:
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, str1, str2).ratio()


def normalize_company_name(name: str) -> str:
    """标准化公司名称"""
    if not name:
        return ''
    
    # 移除常见后缀
    normalized = name.strip()
    for suffix in COMMON_KEYWORDS:
        normalized = re.sub(rf'{suffix}$', '', normalized)
        normalized = re.sub(rf'{suffix}', '', normalized)
    
    return normalized.strip()


def correct_ocr_errors(text: str) -> str:
    """纠正常见的OCR识别错误"""
    corrected = text.strip()
    
    # 尝试多种可能的纠正方式
    possible_corrections = []
    
    for char in corrected:
        if char in OCR_ERROR_MAP:
            alternatives = OCR_ERROR_MAP[char].split()
            for alt in alternatives:
                if alt != char:  # 排除原字符
                    possible_corrections.append((char, alt))
    
    # 如果有可纠正的字符，返回所有可能变体
    if possible_corrections:
        results = [corrected]
        for wrong, correct in possible_corrections:
            new_results = []
            for result in results:
                # 替换第一个匹配
                new_result = result.replace(wrong, correct, 1)
                if new_result not in new_results:
                    new_results.append(new_result)
                # 替换所有匹配
                new_result2 = result.replace(wrong, correct)
                if new_result2 not in new_results:
                    new_results.append(new_result2)
            results = new_results
        return results
    
    return [corrected]


def find_similar_companies(input_name: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
    """
    在数据库中查找相似的公司名称
    
    Args:
        input_name: 输入的公司名称
        threshold: 相似度阈值 (0-1)
    
    Returns:
        匹配的公司列表 [(公司名称, 联系人, 相似度), ...]
    """
    if not input_name or not input_name.strip():
        return []
    
    input_name = input_name.strip()
    
    # 使用原始输入和纠正后的输入进行匹配
    corrected_inputs = correct_ocr_errors(input_name)
    
    # 确保原始输入也在列表中
    if input_name not in corrected_inputs:
        corrected_inputs.insert(0, input_name)
    
    # 为每个纠正后的输入查找匹配
    all_matches = {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取所有活跃的购买单位
    cursor.execute('''
        SELECT unit_name, contact_person, contact_phone 
        FROM purchase_units 
        WHERE is_active = 1
        ORDER BY unit_name
    ''')
    
    units = cursor.fetchall()
    conn.close()
    
    for corrected_input in corrected_inputs:
        normalized_input = normalize_company_name(corrected_input)
        pinyin_input = get_pinyin(normalized_input)
        pinyin_first = get_pinyin_first_letter(normalized_input)
        pinyin_tone_input = get_pinyin_tone(normalized_input)
        
        for unit_name, contact_person, contact_phone in units:
            # 1. 精确匹配（忽略大小写和空格）
            if input_name.lower().replace(' ', '') == unit_name.lower().replace(' ', ''):
                key = unit_name
                if key not in all_matches or all_matches[key][3] < 1.0:
                    all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 1.0)
                continue
            
            # 2. 标准化后匹配
            normalized_unit = normalize_company_name(unit_name)
            if normalized_input.lower() == normalized_unit.lower():
                key = unit_name
                if key not in all_matches or all_matches[key][3] < 0.95:
                    all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 0.95)
                continue
            
            # 3. 拼音首字母匹配
            unit_pinyin_first = get_pinyin_first_letter(normalized_unit)
            if pinyin_first and unit_pinyin_first:
                if pinyin_first == unit_pinyin_first:
                    key = unit_name
                    if key not in all_matches or all_matches[key][3] < 0.9:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 0.9)
                    continue
                similarity = calculate_similarity(pinyin_first, unit_pinyin_first)
                if similarity > 0.8:
                    key = unit_name
                    score = similarity * 0.85
                    if key not in all_matches or all_matches[key][3] < score:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
                    continue
            
            # 4. 完整拼音匹配（无音调）
            unit_pinyin = get_pinyin(normalized_unit)
            if pinyin_input and unit_pinyin:
                pinyin_similarity = calculate_similarity(pinyin_input, unit_pinyin)
                if pinyin_similarity > 0.7:
                    key = unit_name
                    score = pinyin_similarity * 0.8
                    if key not in all_matches or all_matches[key][3] < score:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
                    continue
            
            # 5. 拼音匹配（带音调）- 对于相似的中文字更准确
            unit_pinyin_tone = get_pinyin_tone(normalized_unit)
            if pinyin_tone_input and unit_pinyin_tone:
                pinyin_tone_clean = re.sub(r'\d+', '', pinyin_tone_input)
                unit_pinyin_clean = re.sub(r'\d+', '', unit_pinyin_tone)
                pinyin_similarity = calculate_similarity(pinyin_tone_clean, unit_pinyin_clean)
                if pinyin_similarity > 0.7:
                    key = unit_name
                    score = pinyin_similarity * 0.75
                    if key not in all_matches or all_matches[key][3] < score:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
                    continue
            
            # 6. 特殊规则：拼音核心部分相同（OCR识别错误）
            # 例如：瑞星 vs 蕊芯（拼音核心都是"ruixi"）
            if pinyin_input and unit_pinyin:
                # 使用无声调的拼音进行比较
                pinyin_clean = pinyin_input.replace(' ', '')
                unit_pinyin_clean = unit_pinyin.replace(' ', '')
                
                # 移除常见后缀（家私、公司等）
                for suffix in ['jiasi', 'gongs', 'youxian', 'jituan', 'changdian', 'zhongxin', 'qiy']:
                    pinyin_clean = re.sub(suffix + '$', '', pinyin_clean)
                    unit_pinyin_clean = re.sub(suffix + '$', '', unit_pinyin_clean)
                
                # 如果拼音核心部分（前5个字符）相同
                pinyin_core = pinyin_clean[:5] if len(pinyin_clean) >= 5 else pinyin_clean
                unit_pinyin_core = unit_pinyin_clean[:5] if len(unit_pinyin_clean) >= 5 else unit_pinyin_clean
                
                if pinyin_core == unit_pinyin_core and len(pinyin_core) >= 4:
                    # 拼音核心部分相同（至少4个字符），给予基础分0.65
                    key = unit_name
                    if key not in all_matches or all_matches[key][3] < 0.65:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 0.65)
                    continue
            
            # 6. 中文相似度匹配 - 对于"瑞幸"和"瑞鑫"这种拼音相似但字不同的情况
            try:
                # 检查原始字符串是否包含关系
                if input_name.lower() in unit_name.lower() or unit_name.lower() in input_name.lower():
                    key = unit_name
                    if key not in all_matches or all_matches[key][3] < 0.9:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 0.9)
                    continue
                
                # 检查原始字符串匹配度
                raw_similarity = calculate_similarity(input_name.lower(), unit_name.lower())
                if raw_similarity > 0.5:
                    key = unit_name
                    score = raw_similarity * 0.85
                    if key not in all_matches or all_matches[key][3] < score:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
                    continue
                
                # 检查标准化后的匹配度
                normalized_similarity = calculate_similarity(normalized_input.lower(), normalized_unit.lower())
                if normalized_similarity > 0.5:
                    key = unit_name
                    score = normalized_similarity * 0.8
                    if key not in all_matches or all_matches[key][3] < score:
                        all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
                    continue
                
                # 检查拼音匹配度
                if pinyin_input and unit_pinyin:
                    # 检查输入拼音是否是单位拼音的前缀
                    if pinyin_input in unit_pinyin or unit_pinyin in pinyin_input:
                        key = unit_name
                        if key not in all_matches or all_matches[key][3] < 0.75:
                            all_matches[key] = (unit_name, contact_person or '', contact_phone or '', 0.75)
                        continue
                    
                    # 比较完整拼音
                    pinyin_similarity = calculate_similarity(pinyin_input, unit_pinyin)
                    if pinyin_similarity > 0.7:
                        key = unit_name
                        score = pinyin_similarity * 0.7
                        if key not in all_matches or all_matches[key][3] < score:
                            all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
            except:
                pass
            
            # 7. 字符串相似度匹配（原始字符串）
            similarity = calculate_similarity(normalized_input.lower(), normalized_unit.lower())
            if similarity > threshold:
                key = unit_name
                score = similarity * 0.7
                if key not in all_matches or all_matches[key][3] < score:
                    all_matches[key] = (unit_name, contact_person or '', contact_phone or '', score)
    
    # 转换为列表并按相似度排序
    matches = list(all_matches.values())
    matches.sort(key=lambda x: x[3], reverse=True)
    
    return matches


def match_company_name(input_name: str) -> Optional[dict]:
    """
    匹配公司名称，返回最佳匹配结果
    
    Args:
        input_name: 输入的公司名称
    
    Returns:
        匹配结果或None
    """
    if not input_name or not input_name.strip():
        return None
    
    matches = find_similar_companies(input_name)
    
    if matches:
        best_match = matches[0]
        return {
            'matched_name': best_match[0],
            'contact_person': best_match[1],
            'contact_phone': best_match[2],
            'similarity': best_match[3],
            'all_matches': [
                {'name': m[0], 'contact': m[1], 'similarity': m[3]} 
                for m in matches[:5]
            ]
        }
    
    return None


def get_all_companies() -> List[dict]:
    """获取所有购买单位"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT unit_name, contact_person, contact_phone, address
        FROM purchase_units
        WHERE is_active = 1
        ORDER BY unit_name
    ''')
    
    units = cursor.fetchall()
    conn.close()
    
    return [
        {
            'unit_name': unit[0],
            'contact_person': unit[1] or '',
            'contact_phone': unit[2] or '',
            'address': unit[3] or ''
        }
        for unit in units
    ]


def add_purchase_unit(unit_name: str, contact_person: str = '', 
                      contact_phone: str = '', address: str = '') -> dict:
    """添加新的购买单位"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address)
            VALUES (?, ?, ?, ?)
        ''', (unit_name, contact_person, contact_phone, address))
        
        unit_id = cursor.lastrowid
        conn.commit()
        
        return {
            'success': True,
            'id': unit_id,
            'unit_name': unit_name,
            'contact_person': contact_person,
            'contact_phone': contact_phone,
            'address': address
        }
    except sqlite3.IntegrityError:
        return {
            'success': False,
            'error': f"购买单位 '{unit_name}' 已存在"
        }
    finally:
        conn.close()


if __name__ == '__main__':
    # 测试
    print("测试公司名称匹配:")
    
    # 添加测试数据
    add_purchase_unit('瑞幸咖啡', '张三', '13800138000', '北京')
    add_purchase_unit('星巴克', '李四', '13900139000', '上海')
    
    # 测试匹配
    test_names = ['瑞幸', '瑞幸咖啡', '瑞鑫', '星巴克', '星八克']
    
    for name in test_names:
        result = match_company_name(name)
        if result:
            print(f"  {name} -> {result['matched_name']} (相似度: {result['similarity']:.2f})")
        else:
            print(f"  {name} -> 未找到匹配")
