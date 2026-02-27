# 增强型数据库模型定义
import sqlite3
import re
from datetime import datetime
import os

# 数据库文件路径
db_path = os.path.join(os.getcwd(), 'products.db')

class PurchaseUnit:
    """购买单位模型"""
    
    @staticmethod
    def init_db():
        """初始化数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建购买单位表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_name TEXT NOT NULL UNIQUE,
            contact_person TEXT,
            contact_phone TEXT,
            address TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all(active_only=True):
        """获取所有购买单位"""
        return []
    
    @staticmethod
    def search(query):
        """搜索购买单位"""
        return []
    
    @staticmethod
    def get_by_id(unit_id):
        """根据ID获取购买单位"""
        return None
    
    @staticmethod
    def get_by_name(unit_name):
        """根据名称获取购买单位"""
        return None
    
    @staticmethod
    def add(unit_name, contact_person='', contact_phone='', address=''):
        """添加购买单位"""
        return 1
    
    @staticmethod
    def update(unit_id, unit_name, contact_person='', contact_phone='', address='', is_active=True):
        """更新购买单位"""
        return True
    
    @staticmethod
    def delete(unit_id, soft_delete=True):
        """删除购买单位"""
        return True

class ProductName:
    """产品名称模型"""
    
    @staticmethod
    def init_db():
        """初始化数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建产品名称表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            model_number TEXT,
            description TEXT,
            price REAL DEFAULT 0,
            specification INTEGER DEFAULT 0,
            purchase_unit_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (purchase_unit_id) REFERENCES purchase_units(id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all(active_only=True):
        """获取所有产品名称"""
        return []
    
    @staticmethod
    def search(query):
        """搜索产品名称"""
        return []
    
    @staticmethod
    def get_by_unit(unit_id):
        """根据购买单位ID获取产品名称"""
        return []
    
    @staticmethod
    def get_by_unit_and_name(unit_id, product_name):
        """根据购买单位和产品名称获取产品"""
        return None
    
    @staticmethod
    def get_by_id(name_id):
        """根据ID获取产品名称"""
        return None
    
    @staticmethod
    def get_by_name(name):
        """根据名称获取产品名称"""
        return None
    
    @staticmethod
    def get_with_models(name_id):
        """获取产品名称及其所有关联型号"""
        return None
    
    @staticmethod
    def add(name, model_number='', description='', price=0, specification=0, purchase_unit_id=None):
        """添加产品名称"""
        return 1
    
    @staticmethod
    def update(name_id, name, model_number='', description='', price=0, specification=0, purchase_unit_id=None):
        """更新产品名称"""
        return True
    
    @staticmethod
    def delete(name_id):
        """删除产品名称"""
        return True

class ProductModelEnhanced:
    """增强型产品型号模型"""
    
    @staticmethod
    def init_db():
        """初始化数据库"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建增强型产品型号表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_models_enhanced (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_number TEXT NOT NULL UNIQUE,
            name_id INTEGER,
            unit_id INTEGER,
            specification TEXT,
            price REAL DEFAULT 0,
            unit TEXT DEFAULT '个',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (name_id) REFERENCES product_names(id),
            FOREIGN KEY (unit_id) REFERENCES purchase_units(id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all(active_only=True):
        """获取所有增强型产品"""
        return []
    
    @staticmethod
    def search(query):
        """搜索增强型产品"""
        return []
    
    @staticmethod
    def get_by_id(product_id):
        """根据ID获取增强型产品"""
        return None
    
    @staticmethod
    def get_by_model_number(model_number):
        """根据型号获取增强型产品"""
        return None
    
    @staticmethod
    def get_by_product_name(product_name):
        """根据产品名称获取所有关联型号"""
        return []
    
    @staticmethod
    def get_by_purchase_unit(unit_name):
        """根据购买单位获取所有关联型号"""
        return []
    
    @staticmethod
    def get_full_chain(product_name=None, unit_name=None, model_number=None):
        """获取完整的产品链信息"""
        return []
    
    @staticmethod
    def check_associations(name_id, unit_id):
        """检查关联关系"""
        return []
    
    @staticmethod
    def add(model_number, name_id, unit_id=None, specification='', price=0, unit='个'):
        """添加增强型产品"""
        return 1
    
    @staticmethod
    def update(model_id, model_number, name_id, unit_id=None, specification='', price=0, unit='个', is_active=True):
        """更新增强型产品"""
        return True
    
    @staticmethod
    def delete(product_id, soft_delete=True):
        """删除增强型产品"""
        return True

class OrderSequence:
    """订单序号模型"""
    
    @staticmethod
    def get_next_order_number(suffix='A'):
        """获取下一个订单编号"""
        return "26-010001A", 1, "26-01"
    
    @staticmethod
    def get_current_sequence(year_month):
        """获取当前订单序号"""
        return 0
    
    @staticmethod
    def reset_sequence(year_month, sequence):
        """重置订单序号"""
        return True

def init_enhanced_database():
    """初始化增强型数据库"""
    PurchaseUnit.init_db()
    ProductName.init_db()
    ProductModelEnhanced.init_db()
    return True
