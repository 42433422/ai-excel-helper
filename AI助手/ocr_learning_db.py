#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR识别学习数据库
用于存储图片识别的原始结果和最终用于发货单生成的结果，作为识别学习库
"""

import sqlite3
import json
from datetime import datetime
import logging
import os

# 配置日志编码
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)


class OcrLearningDatabase:
    """OCR识别学习数据库管理类"""
    
    def __init__(self, db_path='ocr_learning.db'):
        """
        初始化数据库
        :param db_path: 数据库文件路径，默认为当前目录下的ocr_learning.db
        """
        # 获取脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(current_dir, db_path)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建OCR识别学习表
                # 存储：图片识别的原始文本结果、最终用于发货单生成的文本结果、对应的商品信息
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ocr_learning_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        -- 图片识别原始结果（OCR识别出来的原始文本）
                        ocr_raw_text TEXT NOT NULL,
                        -- 最终用于发货单生成的文本结果（经过AI解析或人工修正后的文本）
                        final_text TEXT NOT NULL,
                        -- 对应的商品信息（JSON格式，包含商品名称、型号、规格等）
                        product_info TEXT,
                        -- 图片文件路径或标识（可选，用于追溯）
                        image_reference TEXT,
                        -- 识别来源（如：siliconflow、baidu等OCR服务）
                        ocr_source TEXT DEFAULT 'unknown',
                        -- 处理状态（pending: 待处理, confirmed: 已确认, corrected: 已修正）
                        status TEXT DEFAULT 'pending',
                        -- 使用次数（统计该词条被使用的频率）
                        usage_count INTEGER DEFAULT 0,
                        -- 准确率评分（0-1之间，用于评估该词条的可靠性）
                        accuracy_score REAL DEFAULT 0.0,
                        -- 备注信息
                        notes TEXT,
                        -- 创建时间
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        -- 更新时间
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引以提高查询效率
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ocr_raw_text ON ocr_learning_entries(ocr_raw_text)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_final_text ON ocr_learning_entries(final_text)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_status ON ocr_learning_entries(status)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_created_at ON ocr_learning_entries(created_at DESC)
                ''')
                
                conn.commit()
                logger.info("OCR识别学习数据库初始化成功")
                
        except Exception as e:
            logger.error(f"OCR识别学习数据库初始化失败: {e}")
    
    def add_entry(self, ocr_raw_text, final_text, product_info=None, image_reference=None, 
                  ocr_source='unknown', status='pending', notes=''):
        """
        添加一条OCR识别学习词条
        
        :param ocr_raw_text: 图片识别原始结果（OCR识别出来的原始文本）
        :param final_text: 最终用于发货单生成的文本结果
        :param product_info: 对应的商品信息（字典或JSON字符串）
        :param image_reference: 图片文件路径或标识
        :param ocr_source: 识别来源
        :param status: 处理状态
        :param notes: 备注信息
        :return: 新添加词条的ID，失败返回None
        """
        try:
            # 处理product_info，如果是字典则转为JSON字符串
            if product_info is None:
                product_info_json = None
            elif isinstance(product_info, dict):
                product_info_json = json.dumps(product_info, ensure_ascii=False)
            else:
                product_info_json = str(product_info)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在相同的词条（ocr_raw_text和final_text都相同）
                cursor.execute('''
                    SELECT id, usage_count FROM ocr_learning_entries 
                    WHERE ocr_raw_text = ? AND final_text = ?
                ''', (ocr_raw_text, final_text))
                
                existing = cursor.fetchone()
                if existing:
                    # 如果已存在，更新使用次数和更新时间
                    entry_id = existing[0]
                    new_count = existing[1] + 1
                    cursor.execute('''
                        UPDATE ocr_learning_entries 
                        SET usage_count = ?, updated_at = ?
                        WHERE id = ?
                    ''', (new_count, datetime.now(), entry_id))
                    conn.commit()
                    logger.info(f"更新已存在的OCR学习词条: id={entry_id}, usage_count={new_count}")
                    return entry_id
                
                # 插入新词条
                cursor.execute('''
                    INSERT INTO ocr_learning_entries 
                    (ocr_raw_text, final_text, product_info, image_reference, ocr_source, status, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (ocr_raw_text, final_text, product_info_json, image_reference, 
                      ocr_source, status, notes, datetime.now(), datetime.now()))
                
                conn.commit()
                entry_id = cursor.lastrowid
                logger.info(f"添加OCR学习词条成功: id={entry_id}")
                return entry_id
                
        except Exception as e:
            logger.error(f"添加OCR学习词条失败: {e}")
            return None
    
    def get_entry(self, entry_id):
        """
        根据ID获取单条词条
        
        :param entry_id: 词条ID
        :return: 词条字典，不存在返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, ocr_raw_text, final_text, product_info, image_reference,
                           ocr_source, status, usage_count, accuracy_score, notes, created_at, updated_at
                    FROM ocr_learning_entries
                    WHERE id = ?
                ''', (entry_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
                
        except Exception as e:
            logger.error(f"获取OCR学习词条失败: {e}")
            return None
    
    def get_all_entries(self, status=None, limit=None, offset=0):
        """
        获取所有词条
        
        :param status: 按状态筛选（可选）
        :param limit: 限制返回数量
        :param offset: 偏移量
        :return: 词条列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, ocr_raw_text, final_text, product_info, image_reference,
                           ocr_source, status, usage_count, accuracy_score, notes, created_at, updated_at
                    FROM ocr_learning_entries
                '''
                params = []
                
                if status:
                    query += " WHERE status = ?"
                    params.append(status)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                
                cursor.execute(query, params)
                
                entries = []
                for row in cursor.fetchall():
                    entries.append(self._row_to_dict(row))
                
                return entries
                
        except Exception as e:
            logger.error(f"获取OCR学习词条列表失败: {e}")
            return []
    
    def search_entries(self, keyword, search_in_raw=True, search_in_final=True):
        """
        搜索词条
        
        :param keyword: 搜索关键词
        :param search_in_raw: 是否在原始文本中搜索
        :param search_in_final: 是否在最终文本中搜索
        :return: 匹配的词条列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                search_pattern = f'%{keyword}%'
                
                if search_in_raw and search_in_final:
                    query = '''
                        SELECT id, ocr_raw_text, final_text, product_info, image_reference,
                               ocr_source, status, usage_count, accuracy_score, notes, created_at, updated_at
                        FROM ocr_learning_entries
                        WHERE ocr_raw_text LIKE ? OR final_text LIKE ?
                        ORDER BY usage_count DESC, created_at DESC
                    '''
                    params = [search_pattern, search_pattern]
                elif search_in_raw:
                    query = '''
                        SELECT id, ocr_raw_text, final_text, product_info, image_reference,
                               ocr_source, status, usage_count, accuracy_score, notes, created_at, updated_at
                        FROM ocr_learning_entries
                        WHERE ocr_raw_text LIKE ?
                        ORDER BY usage_count DESC, created_at DESC
                    '''
                    params = [search_pattern]
                else:
                    query = '''
                        SELECT id, ocr_raw_text, final_text, product_info, image_reference,
                               ocr_source, status, usage_count, accuracy_score, notes, created_at, updated_at
                        FROM ocr_learning_entries
                        WHERE final_text LIKE ?
                        ORDER BY usage_count DESC, created_at DESC
                    '''
                    params = [search_pattern]
                
                cursor.execute(query, params)
                
                entries = []
                for row in cursor.fetchall():
                    entries.append(self._row_to_dict(row))
                
                return entries
                
        except Exception as e:
            logger.error(f"搜索OCR学习词条失败: {e}")
            return []
    
    def update_entry(self, entry_id, final_text=None, product_info=None, status=None, 
                     accuracy_score=None, notes=None):
        """
        更新词条信息
        
        :param entry_id: 词条ID
        :param final_text: 最终文本（可选）
        :param product_info: 商品信息（可选）
        :param status: 状态（可选）
        :param accuracy_score: 准确率评分（可选）
        :param notes: 备注（可选）
        :return: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if final_text is not None:
                    updates.append("final_text = ?")
                    params.append(final_text)
                
                if product_info is not None:
                    if isinstance(product_info, dict):
                        product_info = json.dumps(product_info, ensure_ascii=False)
                    updates.append("product_info = ?")
                    params.append(product_info)
                
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                
                if accuracy_score is not None:
                    updates.append("accuracy_score = ?")
                    params.append(accuracy_score)
                
                if notes is not None:
                    updates.append("notes = ?")
                    params.append(notes)
                
                if not updates:
                    return True
                
                updates.append("updated_at = ?")
                params.append(datetime.now())
                params.append(entry_id)
                
                query = f"UPDATE ocr_learning_entries SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                logger.info(f"更新OCR学习词条成功: id={entry_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"更新OCR学习词条失败: {e}")
            return False
    
    def delete_entry(self, entry_id):
        """
        删除词条
        
        :param entry_id: 词条ID
        :return: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM ocr_learning_entries WHERE id = ?", (entry_id,))
                conn.commit()
                
                logger.info(f"删除OCR学习词条: id={entry_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"删除OCR学习词条失败: {e}")
            return False
    
    def increment_usage_count(self, entry_id):
        """
        增加词条使用次数
        
        :param entry_id: 词条ID
        :return: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE ocr_learning_entries 
                    SET usage_count = usage_count + 1, updated_at = ?
                    WHERE id = ?
                ''', (datetime.now(), entry_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"增加使用次数失败: {e}")
            return False
    
    def find_similar_entries(self, ocr_raw_text, similarity_threshold=0.8):
        """
        查找相似的词条（基于原始OCR文本）
        
        :param ocr_raw_text: 要比较的OCR原始文本
        :param similarity_threshold: 相似度阈值（0-1之间）
        :return: 相似词条列表
        """
        try:
            entries = self.get_all_entries()
            matches = []
            
            for entry in entries:
                similarity = self._calculate_similarity(ocr_raw_text, entry['ocr_raw_text'])
                if similarity >= similarity_threshold:
                    entry['similarity'] = similarity
                    matches.append(entry)
            
            # 按相似度排序
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            return matches
            
        except Exception as e:
            logger.error(f"查找相似词条失败: {e}")
            return []
    
    def get_statistics(self):
        """
        获取数据库统计信息
        
        :return: 统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总词条数
                cursor.execute("SELECT COUNT(*) FROM ocr_learning_entries")
                total_count = cursor.fetchone()[0]
                
                # 各状态数量
                cursor.execute("SELECT status, COUNT(*) FROM ocr_learning_entries GROUP BY status")
                status_counts = dict(cursor.fetchall())
                
                # 总使用次数
                cursor.execute("SELECT SUM(usage_count) FROM ocr_learning_entries")
                total_usage = cursor.fetchone()[0] or 0
                
                # 平均准确率
                cursor.execute("SELECT AVG(accuracy_score) FROM ocr_learning_entries WHERE accuracy_score > 0")
                avg_accuracy = cursor.fetchone()[0] or 0
                
                return {
                    'total_entries': total_count,
                    'status_counts': status_counts,
                    'total_usage_count': total_usage,
                    'average_accuracy': round(avg_accuracy, 4)
                }
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def _row_to_dict(self, row):
        """将数据库行转换为字典"""
        entry = {
            'id': row[0],
            'ocr_raw_text': row[1],
            'final_text': row[2],
            'product_info': None,
            'image_reference': row[4],
            'ocr_source': row[5],
            'status': row[6],
            'usage_count': row[7],
            'accuracy_score': row[8],
            'notes': row[9],
            'created_at': row[10],
            'updated_at': row[11]
        }
        
        # 解析product_info JSON
        if row[3]:
            try:
                entry['product_info'] = json.loads(row[3])
            except json.JSONDecodeError:
                entry['product_info'] = row[3]
        
        return entry
    
    def _calculate_similarity(self, text1, text2):
        """
        计算两个文本的相似度（使用最长公共子序列算法）
        
        :param text1: 文本1
        :param text2: 文本2
        :return: 相似度（0-1之间）
        """
        if not text1 or not text2:
            return 0.0
        
        if text1 == text2:
            return 1.0
        
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


# 全局数据库实例
_ocr_learning_db = None

def get_ocr_learning_db():
    """获取OCR学习数据库全局实例"""
    global _ocr_learning_db
    if _ocr_learning_db is None:
        _ocr_learning_db = OcrLearningDatabase()
    return _ocr_learning_db


# 初始化数据库
if __name__ == "__main__":
    db = OcrLearningDatabase()
    
    # 添加一些测试数据
    test_entries = [
        {
            'ocr_raw_text': '七彩乐园白底漆20kg 10桶',
            'final_text': '七彩乐园十桶PE白底漆规格20kg',
            'product_info': {
                'name': 'PE白底漆',
                'model_number': 'PE-001',
                'specification': '20kg',
                'quantity': 10,
                'unit': '桶'
            },
            'ocr_source': 'siliconflow',
            'status': 'confirmed',
            'notes': '测试数据'
        },
        {
            'ocr_raw_text': '蕊芯家私固化剂5kg 5桶',
            'final_text': '蕊芯家私五桶固化剂规格5kg',
            'product_info': {
                'name': '固化剂',
                'model_number': 'GHJ-005',
                'specification': '5kg',
                'quantity': 5,
                'unit': '桶'
            },
            'ocr_source': 'siliconflow',
            'status': 'confirmed',
            'notes': '测试数据'
        }
    ]
    
    for entry in test_entries:
        db.add_entry(**entry)
    
    print("OCR识别学习数据库创建完成！")
    print(f"数据库路径: {db.db_path}")
    
    # 显示统计信息
    stats = db.get_statistics()
    print(f"统计信息: {json.dumps(stats, ensure_ascii=False, indent=2)}")
