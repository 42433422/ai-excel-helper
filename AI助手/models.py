# 数据库模型定义
import sqlite3
import re
from datetime import datetime
import os

# 数据库文件路径
db_path = os.path.join(os.getcwd(), 'products.db')

# 验证产品型号是否只包含字母和数字
def is_alphanumeric(model_number):
    """检查字符串是否只包含字母和数字"""
    return bool(re.match(r'^[a-zA-Z0-9]+$', model_number))

class ProductModel:
    """商品数据库模型"""
    
    @staticmethod
    def init_db():
        """初始化数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查是否已有数据需要迁移
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 如果表不存在，创建新表
        if not columns:
            cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT NOT NULL UNIQUE,  -- 产品型号（唯一）
                name TEXT NOT NULL,                -- 产品名称
                specification TEXT,                  -- 规格/描述
                price REAL,                        -- 价格
                quantity INTEGER,                   -- 库存数量
                description TEXT,                   -- 详细描述
                category TEXT,                      -- 产品分类
                brand TEXT,                        -- 品牌
                unit TEXT DEFAULT '个',            -- 单位
                is_active BOOLEAN DEFAULT 1,        -- 是否启用
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        
        # 如果有表但缺少字段，添加字段
        else:
            if 'model_number' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN model_number TEXT")
            if 'category' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN category TEXT")
            if 'brand' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN brand TEXT")
            if 'unit' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT '个'")
            if 'is_active' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT 1")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE products ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        # 添加索引（忽略错误）
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_model_number ON products(model_number)')
        except sqlite3.Error:
            pass  # 忽略索引已存在的错误
            
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)')
        except sqlite3.Error:
            pass
            
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
        except sqlite3.Error:
            pass
            
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC)')
        except sqlite3.Error:
            pass
        
        # 如果有旧数据但缺少model_number，补充默认值
        cursor.execute("SELECT COUNT(*) FROM products WHERE model_number IS NULL OR model_number = ''")
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            cursor.execute("UPDATE products SET model_number = name WHERE model_number IS NULL OR model_number = ''")
        
        # 创建唯一索引（如果不存在）
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_products_model_number ON products(model_number)")
        except sqlite3.IntegrityError:
            # 索引已存在，忽略错误
            pass
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_product(model_number, name, specification='', price=0.0, quantity=0, description='', category='', brand='', unit='个', is_active=True):
        """添加商品"""
        # 验证产品型号是否只包含字母和数字
        if not is_alphanumeric(model_number):
            raise ValueError(f"产品型号 '{model_number}' 只能包含字母和数字")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO products (model_number, name, specification, price, quantity, description, category, brand, unit, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model_number, name, specification, price, quantity, description, category, brand, unit, is_active))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return product_id
    
    @staticmethod
    def get_products():
        """获取所有商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 直接使用表字段名，避免字段顺序问题
        cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
        products = cursor.fetchall()
        
        conn.close()
        
        # 转换为字典列表，使用正确的字段索引
        product_list = []
        for product in products:
            product_list.append({
                'id': product[0],
                'model_number': product[1],  # 正确索引：model_number是第2个字段
                'name': product[2],         # 正确索引：name是第3个字段
                'specification': product[3],  # 正确索引：specification是第4个字段
                'price': product[4],         # 正确索引：price是第5个字段
                'quantity': product[5],      # 正确索引：quantity是第6个字段
                'description': product[6],   # 正确索引：description是第7个字段
                'category': product[7] if len(product) > 7 else '',  # 正确索引：category是第8个字段
                'brand': product[8] if len(product) > 8 else '',     # 正确索引：brand是第9个字段
                'unit': product[9] if len(product) > 9 else '个',    # 正确索引：unit是第10个字段
                'is_active': product[10] if len(product) > 10 else True,  # 正确索引：is_active是第11个字段
                'created_at': product[11] if len(product) > 11 else '',  # 正确索引：created_at是第12个字段
                'updated_at': product[12] if len(product) > 12 else ''  # 正确索引：updated_at是第13个字段
            })
        
        return product_list
    
    @staticmethod
    def get_product(product_id):
        """根据ID获取商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 使用SELECT * 并根据实际表结构映射字段
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        
        conn.close()
        
        if product:
            return {
                'id': product[0],
                'model_number': product[1],  # 正确索引：model_number是第2个字段
                'name': product[2],         # 正确索引：name是第3个字段
                'specification': product[3],  # 正确索引：specification是第4个字段
                'price': product[4],         # 正确索引：price是第5个字段
                'quantity': product[5],      # 正确索引：quantity是第6个字段
                'description': product[6],   # 正确索引：description是第7个字段
                'category': product[7] if len(product) > 7 else '',  # 正确索引：category是第8个字段
                'brand': product[8] if len(product) > 8 else '',     # 正确索引：brand是第9个字段
                'unit': product[9] if len(product) > 9 else '个',    # 正确索引：unit是第10个字段
                'is_active': product[10] if len(product) > 10 else True,  # 正确索引：is_active是第11个字段
                'created_at': product[11] if len(product) > 11 else '',  # 正确索引：created_at是第12个字段
                'updated_at': product[12] if len(product) > 12 else ''  # 正确索引：updated_at是第13个字段
            }
        return None
    
    @staticmethod
    def get_product_by_model(model_number):
        """根据型号获取商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 使用SELECT * 并根据实际表结构映射字段
        cursor.execute('SELECT * FROM products WHERE model_number = ? AND is_active = 1', (model_number,))
        product = cursor.fetchone()
        
        conn.close()
        
        if product:
            return {
                'id': product[0],
                'model_number': product[1],  # 正确索引：model_number是第2个字段
                'name': product[2],         # 正确索引：name是第3个字段
                'specification': product[3],  # 正确索引：specification是第4个字段
                'price': product[4],         # 正确索引：price是第5个字段
                'quantity': product[5],      # 正确索引：quantity是第6个字段
                'description': product[6],   # 正确索引：description是第7个字段
                'category': product[7] if len(product) > 7 else '',  # 正确索引：category是第8个字段
                'brand': product[8] if len(product) > 8 else '',     # 正确索引：brand是第9个字段
                'unit': product[9] if len(product) > 9 else '个',    # 正确索引：unit是第10个字段
                'is_active': product[10] if len(product) > 10 else True,  # 正确索引：is_active是第11个字段
                'created_at': product[11] if len(product) > 11 else '',  # 正确索引：created_at是第12个字段
                'updated_at': product[12] if len(product) > 12 else ''  # 正确索引：updated_at是第13个字段
            }
        return None
    
    @staticmethod
    def update_product(product_id, model_number, name, specification='', price=0.0, quantity=0, description='', category='', brand='', unit='个', is_active=True):
        """更新商品"""
        # 验证产品型号是否只包含字母和数字
        if not is_alphanumeric(model_number):
            raise ValueError(f"产品型号 '{model_number}' 只能包含字母和数字")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE products
        SET model_number = ?, name = ?, specification = ?, price = ?, quantity = ?, description = ?, category = ?, brand = ?, unit = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (model_number, name, specification, price, quantity, description, category, brand, unit, is_active, product_id))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    
    @staticmethod
    def search_products(query):
        """搜索商品（按型号或名称）"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        search_pattern = f'%{query}%'
        # 使用SELECT * 并根据实际表结构映射字段
        cursor.execute('''
        SELECT * FROM products 
        WHERE (model_number LIKE ? OR name LIKE ? OR specification LIKE ?) AND is_active = 1
        ORDER BY created_at DESC
        ''', (search_pattern, search_pattern, search_pattern))
        
        products = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        product_list = []
        for product in products:
            product_list.append({
                'id': product[0],
                'model_number': product[1],  # 正确索引：model_number是第2个字段
                'name': product[2],         # 正确索引：name是第3个字段
                'specification': product[3],  # 正确索引：specification是第4个字段
                'price': product[4],         # 正确索引：price是第5个字段
                'quantity': product[5],      # 正确索引：quantity是第6个字段
                'description': product[6],   # 正确索引：description是第7个字段
                'category': product[7] if len(product) > 7 else '',  # 正确索引：category是第8个字段
                'brand': product[8] if len(product) > 8 else '',     # 正确索引：brand是第9个字段
                'unit': product[9] if len(product) > 9 else '个',    # 正确索引：unit是第10个字段
                'is_active': product[10] if len(product) > 10 else True,  # 正确索引：is_active是第11个字段
                'created_at': product[11] if len(product) > 11 else '',  # 正确索引：created_at是第12个字段
                'updated_at': product[12] if len(product) > 12 else ''  # 正确索引：updated_at是第13个字段
            })
        
        return product_list
    
    @staticmethod
    def delete_product(product_id):
        """删除商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        
        conn.commit()
        conn.close()
        
        return cursor.rowcount > 0
    
    @staticmethod
    def delete_all_products():
        """删除所有商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM products')
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def batch_add_products(products):
        """批量添加商品"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 验证所有产品的型号是否只包含字母和数字
        for product in products:
            model_number = product[0]  # 产品型号是元组的第一个元素
            if not is_alphanumeric(model_number):
                raise ValueError(f"产品型号 '{model_number}' 只能包含字母和数字")
        
        # 使用事务批量插入
        try:
            cursor.executemany('''
            INSERT INTO products (model_number, name, specification, price, quantity, description, category, brand, unit, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', products)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
