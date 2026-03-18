#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建参考配比规则数据库 - 修复版
"""

import sqlite3
import os
from datetime import datetime

def create_ratio_rules_database():
    """创建参考配比规则数据库"""
    
    # 创建数据库路径
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ratio_rules.db')
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建参考配比规则表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratio_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            keywords TEXT NOT NULL,  -- 关键词，逗号分隔
            ratio_data TEXT NOT NULL,  -- 参考配比数据
            created_time TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_time TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 插入参考配比规则 - 修复关键词重叠问题
    ratio_rules = [
        {
            'rule_name': 'PE底漆使用',
            'keywords': 'PE底漆,PE',  # 不包含单独的"底漆"，避免与其他规则冲突
            'ratio_data': '主剂：兰水：稀释剂：白水，100 : 1.2-1.5 : 50-70 : 1.5-1.8'
        },
        {
            'rule_name': 'PU底漆使用',
            'keywords': 'PU底漆,PU',  # 不包含单独的"底漆"，避免与PE规则冲突
            'ratio_data': '主剂：固化剂：稀释剂，１：0.6-0.7：0.4-0.6'
        },
        {
            'rule_name': 'PU亮光漆使用',
            'keywords': 'PU亮光漆,PU亮光,亮光漆',  # 包含"亮光"，与其他规则区分
            'ratio_data': '主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7'
        },
        {
            'rule_name': 'PU哑光漆使用',
            'keywords': 'PU哑光漆,PU哑光,哑光漆',  # 包含"哑光"，与其他规则区分
            'ratio_data': '主剂：固化剂：稀释剂，1：0.5-0.6：0.4-0.8'
        },
        {
            'rule_name': '硝基漆使用',
            'keywords': '硝基漆,硝基,NC漆',  # 硝基漆专用关键词
            'ratio_data': '主剂：稀释剂，1：0.8-1'
        }
    ]
    
    # 清空现有数据
    cursor.execute('DELETE FROM ratio_rules')
    
    # 插入新的规则
    for rule in ratio_rules:
        cursor.execute('''
            INSERT INTO ratio_rules (rule_name, keywords, ratio_data)
            VALUES (?, ?, ?)
        ''', (rule['rule_name'], rule['keywords'], rule['ratio_data']))
    
    # 提交并关闭连接
    conn.commit()
    conn.close()
    
    print(f"✅ 参考配比规则数据库创建成功")
    print(f"📁 数据库路径: {db_path}")
    print(f"📊 已添加 {len(ratio_rules)} 条规则")
    
    # 显示所有规则
    print("\n📋 当前规则列表:")
    for i, rule in enumerate(ratio_rules, 1):
        print(f"{i}. {rule['rule_name']}")
        print(f"   关键词: {rule['keywords']}")
        print(f"   配比: {rule['ratio_data']}")
        print()

if __name__ == '__main__':
    create_ratio_rules_database()
