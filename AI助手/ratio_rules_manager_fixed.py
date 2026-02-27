#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考配比规则管理器 - 修复版
"""

import sqlite3
import os
from typing import Optional, Dict, List

class RatioRulesManager:
    def __init__(self, db_path: str = None):
        """初始化参考配比规则管理器"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ratio_rules.db')
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """确保数据库存在"""
        if not os.path.exists(self.db_path):
            # 如果数据库不存在，创建一个空的
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratio_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    ratio_data TEXT NOT NULL,
                    created_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            conn.commit()
            conn.close()
    
    def match_ratio_by_product_name(self, product_name: str) -> Optional[str]:
        """根据产品名称匹配参考配比 - 修复版"""
        if not product_name or not product_name.strip():
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询所有激活的规则
        cursor.execute('''
            SELECT rule_name, keywords, ratio_data FROM ratio_rules 
            WHERE is_active = 1
            ORDER BY id
        ''')
        
        rules = cursor.fetchall()
        conn.close()
        
        product_name_lower = product_name.lower()
        
        # 按优先级匹配 - 更精确的匹配在前
        priority_matches = []
        fallback_matches = []
        
        for rule_row in rules:
            rule_name, keywords, ratio_data = rule_row
            keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
            
            # 检查是否有精确匹配（关键词完整包含在产品名称中）
            exact_match = False
            for keyword in keyword_list:
                if keyword in product_name_lower:
                    exact_match = True
                    # 按关键词长度排序，优先匹配更长的关键词
                    priority_matches.append((len(keyword), ratio_data))
                    break
            
            if not exact_match:
                # 如果没有精确匹配，收集作为后备
                for keyword in keyword_list:
                    if keyword in product_name_lower:
                        fallback_matches.append((len(keyword), ratio_data))
                        break
        
        # 优先返回最长匹配的精确匹配
        if priority_matches:
            priority_matches.sort(key=lambda x: x[0], reverse=True)
            return priority_matches[0][1]
        
        # 如果没有精确匹配，返回最长匹配的后备匹配
        if fallback_matches:
            fallback_matches.sort(key=lambda x: x[0], reverse=True)
            return fallback_matches[0][1]
        
        return None
    
    def get_all_rules(self) -> List[Dict]:
        """获取所有规则"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rule_name, keywords, ratio_data, is_active
            FROM ratio_rules
            ORDER BY id
        ''')
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                'rule_name': row[0],
                'keywords': row[1],
                'ratio_data': row[2],
                'is_active': bool(row[3])
            })
        
        conn.close()
        return rules
    
    def test_matching(self, test_products: List[str]) -> Dict[str, Optional[str]]:
        """测试匹配功能"""
        results = {}
        for product_name in test_products:
            matched_ratio = self.match_ratio_by_product_name(product_name)
            results[product_name] = matched_ratio
        return results

# 测试代码
if __name__ == '__main__':
    # 创建管理器
    manager = RatioRulesManager()
    
    # 测试匹配功能
    test_products = [
        'PE底漆面漆',
        'PU底漆稀释剂',
        'PU亮光漆稀释剂',
        'PU哑光漆固化剂',
        '硝基漆稀释剂',
        '不匹配的产品',
        'PU固化剂',  # 这个应该不匹配（包含"剂"）
        'PU面漆稀释剂',  # 这个应该匹配PU相关的规则
        'PE稀释剂',  # 这个应该匹配PE的规则
    ]
    
    print("🧪 测试修复后的参考配比匹配功能")
    print("=" * 60)
    
    results = manager.test_matching(test_products)
    for product, ratio in results.items():
        print(f"📦 {product}")
        print(f"   匹配结果: {ratio if ratio else '无匹配'}")
        print()
    
    # 显示所有规则
    print("📋 当前规则列表:")
    rules = manager.get_all_rules()
    for i, rule in enumerate(rules, 1):
        print(f"{i}. {rule['rule_name']} {'(禁用)' if not rule['is_active'] else ''}")
        print(f"   关键词: {rule['keywords']}")
        print(f"   配比: {rule['ratio_data']}")
        print()
