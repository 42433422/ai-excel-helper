#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音模板学习样板数据库
"""

import sqlite3
import json
from datetime import datetime
import logging

# 配置日志编码
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

class VoiceLearningDatabase:
    def __init__(self, db_path='voice_learning.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建语音学习样板表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS voice_learning_samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wrong_input TEXT NOT NULL,
                        correct_output TEXT NOT NULL,
                        category TEXT NOT NULL,
                        context TEXT,
                        usage_count INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # 创建学习记录表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS learning_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sample_id INTEGER,
                        original_text TEXT NOT NULL,
                        corrected_text TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1,
                        feedback TEXT,
                        FOREIGN KEY (sample_id) REFERENCES voice_learning_samples (id)
                    )
                ''')
                
                conn.commit()
                logger.info("语音学习样板数据库初始化成功")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def add_sample(self, wrong_input, correct_output, category, context=""):
        """添加学习样板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在
                cursor.execute('''
                    SELECT id FROM voice_learning_samples 
                    WHERE wrong_input = ? AND correct_output = ?
                ''', (wrong_input, correct_output))
                
                existing = cursor.fetchone()
                if existing:
                    return existing[0]
                
                cursor.execute('''
                    INSERT INTO voice_learning_samples 
                    (wrong_input, correct_output, category, context, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (wrong_input, correct_output, category, context, datetime.now()))
                
                conn.commit()
                sample_id = cursor.lastrowid
                logger.info(f"添加学习样板: {wrong_input} -> {correct_output}")
                return sample_id
                
        except Exception as e:
            logger.error(f"添加学习样板失败: {e}")
            return None
    
    def get_all_samples(self, category=None, active_only=True):
        """获取所有学习样板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, wrong_input, correct_output, category, context, 
                           usage_count, success_rate, is_active, created_at
                    FROM voice_learning_samples
                '''
                
                params = []
                conditions = []
                
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                
                if active_only:
                    conditions.append("is_active = 1")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY usage_count DESC, success_rate DESC"
                
                cursor.execute(query, params)
                samples = []
                for row in cursor.fetchall():
                    samples.append({
                        'id': row[0],
                        'wrong_input': row[1],
                        'correct_output': row[2],
                        'category': row[3],
                        'context': row[4],
                        'usage_count': row[5],
                        'success_rate': row[6],
                        'is_active': row[7],
                        'created_at': row[8]
                    })
                
                return samples
                
        except Exception as e:
            logger.error(f"获取学习样板失败: {e}")
            return []
    
    def update_sample(self, sample_id, wrong_input=None, correct_output=None, 
                    category=None, context=None, is_active=None):
        """更新学习样板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建更新语句
                updates = []
                params = []
                
                if wrong_input is not None:
                    updates.append("wrong_input = ?")
                    params.append(wrong_input)
                
                if correct_output is not None:
                    updates.append("correct_output = ?")
                    params.append(correct_output)
                
                if category is not None:
                    updates.append("category = ?")
                    params.append(category)
                
                if context is not None:
                    updates.append("context = ?")
                    params.append(context)
                
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(is_active)
                
                updates.append("updated_at = ?")
                params.append(datetime.now())
                params.append(sample_id)
                
                query = f"UPDATE voice_learning_samples SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                logger.info(f"更新学习样板: {sample_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新学习样板失败: {e}")
            return False
    
    def delete_sample(self, sample_id):
        """删除学习样板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM voice_learning_samples WHERE id = ?", (sample_id,))
                conn.commit()
                
                logger.info(f"删除学习样板: {sample_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除学习样板失败: {e}")
            return False
    
    def apply_sample(self, sample_id, original_text, corrected_text, success=True, feedback=""):
        """记录样板应用"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 添加应用记录
                cursor.execute('''
                    INSERT INTO learning_records 
                    (sample_id, original_text, corrected_text, success, feedback)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sample_id, original_text, corrected_text, success, feedback))
                
                # 更新样板统计
                cursor.execute('''
                    UPDATE voice_learning_samples 
                    SET usage_count = usage_count + 1,
                        success_rate = CASE 
                            WHEN usage_count = 0 THEN ?
                            ELSE (success_rate * usage_count + ?) / (usage_count + 1)
                        END
                    WHERE id = ?
                ''', (1.0 if success else 0.0, 1.0 if success else 0.0, sample_id))
                
                conn.commit()
                logger.info(f"记录样板应用: {sample_id}")
                return True
                
        except Exception as e:
            logger.error(f"记录样板应用失败: {e}")
            return False
    
    def search_samples(self, text, similarity_threshold=0.8):
        """搜索相似样板"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, wrong_input, correct_output, category
                    FROM voice_learning_samples
                    WHERE is_active = 1
                ''')
                
                all_samples = cursor.fetchall()
                matches = []
                
                for sample in all_samples:
                    similarity = self.calculate_similarity(text.lower(), sample[1].lower())
                    if similarity >= similarity_threshold:
                        matches.append({
                            'id': sample[0],
                            'wrong_input': sample[1],
                            'correct_output': sample[2],
                            'category': sample[3],
                            'similarity': similarity
                        })
                
                return sorted(matches, key=lambda x: x['similarity'], reverse=True)
                
        except Exception as e:
            logger.error(f"搜索样板失败: {e}")
            return []
    
    def calculate_similarity(self, text1, text2):
        """计算文本相似度（简单实现）"""
        # 使用简单的字符匹配算法
        if text1 == text2:
            return 1.0
        
        if not text1 or not text2:
            return 0.0
        
        # 计算最长公共子序列长度
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(text1, text2)
        max_len = max(len(text1), len(text2))
        
        return lcs_len / max_len if max_len > 0 else 0.0

# 初始化数据库
if __name__ == "__main__":
    # 创建默认学习样板
    db = VoiceLearningDatabase()
    
    # 添加一些默认的学习样板
    default_samples = [
        ("瑞星", "蕊芯家私", "客户单位", "客户名称谐音"),
        ("批", "PE", "产品类型", "化学标识谐音"),
        ("优雅白", "哑光", "产品特性", "产品名称谐音"),
        ("武统", "固化剂", "产品类型", "产品类型谐音"),
        ("180千克", "180KG", "产品规格", "单位格式"),
        ("180kG", "180KG", "产品规格", "单位格式")
    ]
    
    for wrong, correct, category, context in default_samples:
        db.add_sample(wrong, correct, category, context)
    
    print("语音学习样板数据库创建完成！")