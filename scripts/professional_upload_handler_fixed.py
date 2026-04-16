"""
专业版上传功能处理器（修复版）
用于处理购买单位和产品数据的导入，确保上下文正确识别
使用customer数据库存储购买单位信息
"""

import sqlite3
import os
from datetime import datetime
import re

class ProfessionalUploadHandlerFixed:
    """专业版上传处理器（修复版）"""
    
    def __init__(self):
        # 产品数据库
        self.products_db = "e:/FHD/98k/AI助手/AI助手/products.db"
        # 客户数据库（存储购买单位）
        self.customers_db = "e:/FHD/424/customers.db"
        self.upload_context = None
        
    def set_upload_context(self, context_data):
        """设置上传上下文"""
        self.upload_context = context_data
        print(f"📝 设置上传上下文: {context_data}")
        
    def detect_file_type(self, file_path):
        """检测文件类型"""
        if file_path.endswith('.db'):
            return 'sqlite_database'
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            return 'excel_spreadsheet'
        elif file_path.endswith('.csv'):
            return 'csv_file'
        else:
            return 'unknown'
    
    def analyze_sqlite_database(self, db_path):
        """分析SQLite数据库结构"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            analysis_result = {
                'file_type': 'sqlite_database',
                'tables': [],
                'suggested_action': None
            }
            
            for table in tables:
                table_name = table[0]
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # 获取数据样本
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                table_info = {
                    'name': table_name,
                    'columns': [{'name': col[1], 'type': col[2]} for col in columns],
                    'row_count': row_count
                }
                
                analysis_result['tables'].append(table_info)
                
                # 检测是否为产品表
                if 'products' in table_name.lower():
                    analysis_result['suggested_action'] = 'import_products'
                    
                    # 从文件名推断购买单位
                    file_name = os.path.basename(db_path)
                    unit_name = file_name.replace('.db', '').strip()
                    analysis_result['purchase_unit'] = unit_name
            
            conn.close()
            return analysis_result
            
        except Exception as e:
            return {'error': str(e)}
    
    def ensure_purchase_units_table(self, cursor):
        """确保purchase_units表存在"""
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("📋 创建purchase_units表...")
            cursor.execute('''
                CREATE TABLE purchase_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_name TEXT NOT NULL UNIQUE,
                    contact_person TEXT,
                    contact_phone TEXT,
                    address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add_purchase_unit_to_customer_db(self, unit_name):
        """添加购买单位到customer数据库"""
        try:
            conn = sqlite3.connect(self.customers_db)
            cursor = conn.cursor()
            
            # 确保表存在
            self.ensure_purchase_units_table(cursor)
            
            # 检查是否已存在
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", (unit_name,))
            existing_unit = cursor.fetchone()
            
            if existing_unit:
                print(f"✅ 购买单位 '{unit_name}' 已存在于customer数据库中")
                conn.close()
                return True
            
            # 添加新购买单位
            cursor.execute("""
                INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (unit_name, "", "", ""))
            
            conn.commit()
            print(f"✅ 购买单位 '{unit_name}' 已成功添加到customer数据库")
            
            # 验证添加结果
            cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
            new_count = cursor.fetchone()[0]
            print(f"📊 customer数据库中活跃购买单位数量: {new_count}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ 添加购买单位到customer数据库时出错: {e}")
            return False
    
    def process_upload_response(self, user_response, file_path):
        """处理用户上传后的响应"""
        print(f"🔍 处理用户响应: {user_response}")
        print(f"📁 文件路径: {file_path}")
        
        # 检测文件类型
        file_type = self.detect_file_type(file_path)
        print(f"📊 文件类型: {file_type}")
        
        if file_type == 'sqlite_database':
            # 分析数据库
            analysis = self.analyze_sqlite_database(file_path)
            
            if 'error' in analysis:
                return {
                    'success': False,
                    'message': f'数据库分析失败: {analysis["error"]}'
                }
            
            # 检查是否有产品表
            if analysis.get('suggested_action') == 'import_products':
                purchase_unit = analysis.get('purchase_unit', '未知单位')
                
                # 处理用户响应
                if user_response.lower() in ['是', 'yes', 'y', '确认', '确认导入']:
                    return self._import_products_from_db(file_path, purchase_unit)
                elif user_response.lower() in ['否', 'no', 'n', '取消']:
                    return {
                        'success': True,
                        'message': '用户取消了导入操作'
                    }
                elif '改成' in user_response or '改为' in user_response:
                    # 提取新的购买单位名称
                    new_unit = self._extract_unit_name(user_response)
                    if new_unit:
                        return self._import_products_from_db(file_path, new_unit)
                    else:
                        return {
                            'success': False,
                            'message': '无法从响应中提取购买单位名称，请明确指定'
                        }
                else:
                    return {
                        'success': False,
                        'message': '无法识别的响应，请回复"是"确认导入，或"否"取消，或"改成<名称>"指定购买单位'
                    }
            else:
                return {
                    'success': False,
                    'message': '数据库中没有找到产品表，无法进行导入'
                }
        else:
            return {
                'success': False,
                'message': f'不支持的文件类型: {file_type}'
            }
    
    def _extract_unit_name(self, response):
        """从用户响应中提取购买单位名称"""
        # 匹配模式：改成 XXX 或 改为 XXX
        patterns = [
            r'改成\s*(.+)',
            r'改为\s*(.+)',
            r'change to\s*(.+)',
            r'rename to\s*(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                unit_name = match.group(1).strip()
                # 移除可能的标点符号
                unit_name = re.sub(r'[。，！？,.!?]', '', unit_name)
                return unit_name
        
        return None
    
    def _import_products_from_db(self, source_db, purchase_unit):
        """从数据库导入产品数据（修复版）"""
        try:
            # 第一步：添加购买单位到customer数据库
            print(f"📝 第一步：添加购买单位 '{purchase_unit}' 到customer数据库")
            unit_added = self.add_purchase_unit_to_customer_db(purchase_unit)
            
            if not unit_added:
                return {
                    'success': False,
                    'message': f'添加购买单位到customer数据库失败'
                }
            
            # 第二步：导入产品数据到products数据库
            print(f"📝 第二步：导入产品数据到products数据库")
            
            # 连接源数据库
            source_conn = sqlite3.connect(source_db)
            source_cursor = source_conn.cursor()
            
            # 连接目标数据库
            target_conn = sqlite3.connect(self.products_db)
            target_cursor = target_conn.cursor()
            
            # 确保目标数据库表存在
            self._ensure_products_table_exists(target_cursor)
            
            # 获取源数据库产品数据
            source_cursor.execute("SELECT * FROM products")
            source_products = source_cursor.fetchall()
            
            imported_count = 0
            skipped_count = 0
            
            for product in source_products:
                # 源数据库结构: id, model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at
                source_id, model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at = product
                
                # 检查目标数据库中是否已存在相同型号的产品
                target_cursor.execute("SELECT id FROM products WHERE model_number = ?", (model_number,))
                existing_product = target_cursor.fetchone()
                
                if existing_product:
                    skipped_count += 1
                    continue
                
                # 插入新产品，添加购买单位标识
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 在描述中添加购买单位标识
                description_with_unit = f"[{purchase_unit}] {description if description else ''}".strip()
                
                insert_sql = """
                INSERT INTO products (model_number, name, specification, price, quantity, description, category, brand, unit, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                target_cursor.execute(insert_sql, (
                    model_number, name, specification, price, quantity, 
                    description_with_unit, category, brand, unit, is_active,
                    current_time, current_time
                ))
                
                imported_count += 1
            
            # 提交事务
            target_conn.commit()
            
            # 关闭连接
            source_conn.close()
            target_conn.close()
            
            return {
                'success': True,
                'message': f'✅ 导入完成！成功导入 {imported_count} 个产品，跳过 {skipped_count} 个已存在产品',
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'purchase_unit': purchase_unit,
                'customer_db_updated': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'导入失败: {str(e)}'
            }
    
    def _ensure_products_table_exists(self, cursor):
        """确保products表存在"""
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                specification TEXT,
                price REAL,
                quantity INTEGER DEFAULT 0,
                description TEXT,
                category TEXT,
                brand TEXT,
                unit TEXT DEFAULT '个',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

def simulate_professional_upload_fixed():
    """模拟专业版上传流程（修复版）"""
    handler = ProfessionalUploadHandlerFixed()
    
    # 模拟上传文件
    file_path = "e:/FHD/424/半岛风情.db"
    
    # 第一步：分析文件
    print("=== 专业版上传功能模拟（修复版） ===")
    print("📎 文件分析完成: 半岛风情.db")
    print("解析器: sqlite_db")
    print("分析结果: 已识别 SQLite 数据库（.db）。库内表数：1；主要表：products。")
    print("建议下一步用途：unit_products_db。")
    print("下一步：请到聊天里回复'是'以导入购买单位「半岛风情」的产品；也可回复'否 / 改成 <名称>'")
    print()
    
    # 第二步：模拟用户响应
    user_responses = [
        "是",  # 确认导入
        "改成 半岛家具",  # 修改购买单位名称
        "否",  # 取消导入
    ]
    
    for response in user_responses:
        print(f"🤖 用户回复: {response}")
        result = handler.process_upload_response(response, file_path)
        print(f"📋 处理结果: {result}")
        print("-" * 50)

if __name__ == "__main__":
    simulate_professional_upload_fixed()