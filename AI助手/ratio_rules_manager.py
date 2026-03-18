#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考配比规则管理器
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
        """根据产品名称匹配参考配比"""
        if not product_name or not product_name.strip():
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询所有激活的规则
        cursor.execute('''
            SELECT ratio_data FROM ratio_rules 
            WHERE is_active = 1
        ''')
        
        rules = cursor.fetchall()
        conn.close()
        
        product_name_lower = product_name.lower()
        
        # 检查每个规则的关键词是否匹配
        for rule_row in rules:
            ratio_data = rule_row[0]
            
            # 获取该规则的关键词
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keywords FROM ratio_rules 
                WHERE ratio_data = ? AND is_active = 1
            ''', (ratio_data,))
            
            rule_row = cursor.fetchone()
            conn.close()
            
            if rule_row:
                keywords = rule_row[0]
                keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
                
                # 检查产品名称是否包含任何关键词
                for keyword in keyword_list:
                    if keyword in product_name_lower:
                        return ratio_data
        
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
    
    def add_rule(self, rule_name: str, keywords: str, ratio_data: str) -> bool:
        """添加新规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ratio_rules (rule_name, keywords, ratio_data)
                VALUES (?, ?, ?)
            ''', (rule_name, keywords, ratio_data))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加规则失败: {e}")
            return False
    
    def update_rule(self, rule_name: str, keywords: str = None, ratio_data: str = None, is_active: bool = None) -> bool:
        """更新规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建更新查询
            update_fields = []
            params = []
            
            if keywords is not None:
                update_fields.append("keywords = ?")
                params.append(keywords)
            
            if ratio_data is not None:
                update_fields.append("ratio_data = ?")
                params.append(ratio_data)
            
            if is_active is not None:
                update_fields.append("is_active = ?")
                params.append(is_active)
            
            if update_fields:
                update_fields.append("updated_time = ?")
                params.append(datetime.now().isoformat())
                params.append(rule_name)
                
                query = f'''
                    UPDATE ratio_rules 
                    SET {', '.join(update_fields)}
                    WHERE rule_name = ?
                '''
                
                cursor.execute(query, params)
                conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"更新规则失败: {e}")
            return False
    
    def delete_rule(self, rule_name: str) -> bool:
        """删除规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM ratio_rules WHERE rule_name = ?
            ''', (rule_name,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除规则失败: {e}")
            return False
    
    def test_matching(self, test_products: List[str]) -> Dict[str, Optional[str]]:
        """测试匹配功能"""
        results = {}
        for product_name in test_products:
            matched_ratio = self.match_ratio_by_product_name(product_name)
            results[product_name] = matched_ratio
        return results

# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    os.system('python create_ratio_rules_db.py')
    
    # 创建管理器
    manager = RatioRulesManager()
    
    # 测试匹配功能
    test_products = [
        'PE底漆面漆',
        'PU底漆稀释剂',
        'PU亮光漆稀释剂',
        'PU哑光漆固化剂',
        '硝基漆稀释剂',
        '不匹配的产品'
    ]
    
    print("🧪 测试参考配比匹配功能")
    print("=" * 50)
    
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
