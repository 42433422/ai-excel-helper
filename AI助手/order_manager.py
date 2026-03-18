#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单管理器
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class OrderManager:
    """订单管理器"""
    
    def __init__(self, db_path: str = None):
        """初始化"""
        if db_path is None:
            self.db_path = 'products.db'  # 使用products.db作为主要数据源
        else:
            self.db_path = db_path
    
    def create_order(self, order_data: Dict) -> Dict:
        """
        创建订单
        
        Args:
            order_data: 订单数据字典
                {
                    'order_number': 订单编号,
                    'purchase_unit': 购买单位,
                    'unit_id': 单位ID,
                    'products': 产品列表,
                    'total_amount': 总金额,
                    'total_quantity_kg': 总公斤数,
                    'total_quantity_tins': 总桶数,
                    'raw_text': 原始文本,
                    'parsed_data': 解析数据
                }
        
        Returns:
            订单信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保orders表存在
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT UNIQUE NOT NULL,
                    purchase_unit TEXT NOT NULL,
                    unit_id INTEGER,
                    total_amount REAL DEFAULT 0,
                    total_quantity_kg REAL DEFAULT 0,
                    total_quantity_tins INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    raw_text TEXT,
                    parsed_data TEXT,
                    FOREIGN KEY (unit_id) REFERENCES purchase_units(id)
                )
            ''')
            
            # 为order_number添加索引，提高搜索性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number)')
            
            # 确保shipment_records表存在order_id字段
            try:
                # 检查order_id字段是否存在
                cursor.execute('PRAGMA table_info(shipment_records);')
                columns = cursor.fetchall()
                has_order_id = any('order_id' in column[1] for column in columns)
                
                if not has_order_id:
                    cursor.execute('ALTER TABLE shipment_records ADD COLUMN order_id INTEGER')
            except:
                pass
            
            # 计算总金额和总数量（如果未提供）
            total_amount = order_data.get('total_amount', 0)
            total_quantity_kg = order_data.get('total_quantity_kg', 0)
            total_quantity_tins = order_data.get('total_quantity_tins', 0)
            
            products = order_data.get('products', [])
            if products and (not total_amount or not total_quantity_kg):
                total_amount = sum(p.get('amount', 0) for p in products)
                total_quantity_kg = sum(p.get('quantity_kg', 0) for p in products)
                total_quantity_tins = sum(p.get('quantity_tins', 0) for p in products)
            
            # 检查订单是否已存在，如果存在则删除旧订单
            order_number = order_data.get('order_number', '')
            cursor.execute('SELECT id FROM orders WHERE order_number = ?', (order_number,))
            existing_order = cursor.fetchone()
            if existing_order:
                existing_id = existing_order[0]
                logger.info(f"订单 {order_number} 已存在，删除旧订单 (ID: {existing_id})")
                cursor.execute('DELETE FROM shipment_records WHERE order_id = ?', (existing_id,))
                cursor.execute('DELETE FROM orders WHERE id = ?', (existing_id,))
            
            # 创建订单主记录
            cursor.execute('''
                INSERT INTO orders (
                    order_number, purchase_unit, unit_id, total_amount,
                    total_quantity_kg, total_quantity_tins, raw_text, parsed_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_data.get('order_number', ''),
                order_data.get('purchase_unit', ''),
                order_data.get('unit_id'),
                total_amount,
                total_quantity_kg,
                total_quantity_tins,
                order_data.get('raw_text', ''),
                json.dumps(order_data.get('parsed_data', {})) if order_data.get('parsed_data') else ''
            ))
            
            order_id = cursor.lastrowid
            
            # 创建产品记录
            product_records = []
            for product in products:
                cursor.execute('''
                    INSERT INTO shipment_records (
                        purchase_unit, unit_id, order_id, product_name, model_number,
                        quantity_kg, quantity_tins, tin_spec, unit_price, amount,
                        raw_text, parsed_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_data.get('purchase_unit', ''),
                    order_data.get('unit_id'),
                    order_id,
                    product.get('name', ''),
                    product.get('model_number', ''),
                    product.get('quantity_kg', 0),
                    product.get('quantity_tins', 0),
                    product.get('tin_spec', 10.0),
                    product.get('unit_price', 0),
                    product.get('amount', 0),
                    order_data.get('raw_text', ''),
                    json.dumps(product) if product else ''
                ))
                product_records.append(cursor.lastrowid)
            
            conn.commit()
            conn.close()
            
            logger.info(f"创建订单成功: {order_data.get('order_number')}, 订单ID: {order_id}")
            
            return {
                'order_id': order_id,
                'order_number': order_data.get('order_number'),
                'purchase_unit': order_data.get('purchase_unit'),
                'total_amount': total_amount,
                'total_quantity_kg': total_quantity_kg,
                'total_quantity_tins': total_quantity_tins,
                'product_count': len(products),
                'product_records': product_records,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            raise
    
    def get_order_by_number(self, order_number: str) -> Optional[Dict]:
        """
        根据订单编号获取订单
        
        Args:
            order_number: 订单编号
        
        Returns:
            订单信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取订单主信息
            cursor.execute('''
                SELECT id, order_number, purchase_unit, unit_id, total_amount,
                       total_quantity_kg, total_quantity_tins, status,
                       created_at, updated_at, raw_text, parsed_data
                FROM orders
                WHERE order_number = ?
            ''', (order_number,))
            
            order_row = cursor.fetchone()
            if not order_row:
                conn.close()
                return None
            
            # 获取订单产品
            cursor.execute('''
                SELECT id, product_name, model_number, quantity_kg, quantity_tins,
                       tin_spec, unit_price, amount, status
                FROM shipment_records
                WHERE order_id = ?
            ''', (order_row[0],))
            
            products = []
            for product_row in cursor.fetchall():
                products.append({
                    'id': product_row[0],
                    'name': product_row[1],
                    'model_number': product_row[2],
                    'quantity_kg': product_row[3],
                    'quantity_tins': product_row[4],
                    'tin_spec': product_row[5],
                    'unit_price': product_row[6],
                    'amount': product_row[7],
                    'status': product_row[8]
                })
            
            conn.close()
            
            order_info = {
                'id': order_row[0],
                'order_number': order_row[1],
                'purchase_unit': order_row[2],
                'unit_id': order_row[3],
                'total_amount': order_row[4],
                'total_quantity_kg': order_row[5],
                'total_quantity_tins': order_row[6],
                'status': order_row[7],
                'created_at': order_row[8],
                'updated_at': order_row[9],
                'raw_text': order_row[10],
                'parsed_data': json.loads(order_row[11]) if order_row[11] else {},
                'products': products
            }
            
            return order_info
            
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return None
    
    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """
        根据订单ID获取订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            订单信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取订单主信息
            cursor.execute('''
                SELECT id, order_number, purchase_unit, unit_id, total_amount,
                       total_quantity_kg, total_quantity_tins, status,
                       created_at, updated_at, raw_text, parsed_data
                FROM orders
                WHERE id = ?
            ''', (order_id,))
            
            order_row = cursor.fetchone()
            if not order_row:
                conn.close()
                return None
            
            # 获取订单产品
            cursor.execute('''
                SELECT id, product_name, model_number, quantity_kg, quantity_tins,
                       tin_spec, unit_price, amount, status
                FROM shipment_records
                WHERE order_id = ?
            ''', (order_row[0],))
            
            products = []
            for product_row in cursor.fetchall():
                products.append({
                    'id': product_row[0],
                    'name': product_row[1],
                    'model_number': product_row[2],
                    'quantity_kg': product_row[3],
                    'quantity_tins': product_row[4],
                    'tin_spec': product_row[5],
                    'unit_price': product_row[6],
                    'amount': product_row[7],
                    'status': product_row[8]
                })
            
            conn.close()
            
            order_info = {
                'id': order_row[0],
                'order_number': order_row[1],
                'purchase_unit': order_row[2],
                'unit_id': order_row[3],
                'total_amount': order_row[4],
                'total_quantity_kg': order_row[5],
                'total_quantity_tins': order_row[6],
                'status': order_row[7],
                'created_at': order_row[8],
                'updated_at': order_row[9],
                'raw_text': order_row[10],
                'parsed_data': json.loads(order_row[11]) if order_row[11] else {},
                'products': products
            }
            
            return order_info
            
        except Exception as e:
            logger.error(f"获取订单失败: {e}")
            return None
    
    def search_orders(self, query: str) -> List[Dict]:
        """
        搜索订单
        
        Args:
            query: 搜索关键词（订单编号、购买单位等）
        
        Returns:
            订单列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 搜索订单编号或购买单位
            cursor.execute('''
                SELECT id, order_number, purchase_unit, total_amount,
                       total_quantity_kg, total_quantity_tins, status,
                       created_at
                FROM orders
                WHERE order_number LIKE ? OR purchase_unit LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            ''', (f'%{query}%', f'%{query}%'))
            
            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'id': row[0],
                    'order_number': row[1],
                    'purchase_unit': row[2],
                    'total_amount': row[3],
                    'total_quantity_kg': row[4],
                    'total_quantity_tins': row[5],
                    'status': row[6],
                    'created_at': row[7]
                })
            
            conn.close()
            return orders
            
        except Exception as e:
            logger.error(f"搜索订单失败: {e}")
            return []
    
    def get_all_orders(self, limit: int = 100) -> List[Dict]:
        """
        获取所有订单
        
        Args:
            limit: 限制数量
        
        Returns:
            订单列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, order_number, purchase_unit, total_amount,
                       total_quantity_kg, total_quantity_tins, status,
                       created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'id': row[0],
                    'order_number': row[1],
                    'purchase_unit': row[2],
                    'total_amount': row[3],
                    'total_quantity_kg': row[4],
                    'total_quantity_tins': row[5],
                    'status': row[6],
                    'created_at': row[7]
                })
            
            conn.close()
            return orders
            
        except Exception as e:
            logger.error(f"获取所有订单失败: {e}")
            return []
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """
        更新订单状态

        Args:
            order_id: 订单ID
            status: 状态

        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE orders
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, order_id))

            # 同时更新相关产品记录的状态
            cursor.execute('''
                UPDATE shipment_records
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            ''', (status, order_id))

            conn.commit()
            conn.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")
            return False

    def update_order_number(self, order_id: int, new_order_number: str) -> bool:
        """
        更新订单编号

        Args:
            order_id: 订单ID
            new_order_number: 新订单编号

        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查新订单编号是否已存在
            cursor.execute('''
                SELECT id FROM orders
                WHERE order_number = ? AND id != ?
            ''', (new_order_number, order_id))

            if cursor.fetchone():
                conn.close()
                return False  # 订单编号已存在

            # 更新订单编号
            cursor.execute('''
                UPDATE orders
                SET order_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_order_number, order_id))

            conn.commit()
            conn.close()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"更新订单编号失败: {e}")
            return False

# 便捷函数
def create_order(order_data: Dict, db_path: str = None) -> Dict:
    """创建订单"""
    manager = OrderManager(db_path)
    return manager.create_order(order_data)

def get_order_by_number(order_number: str, db_path: str = None) -> Optional[Dict]:
    """根据订单编号获取订单"""
    manager = OrderManager(db_path)
    return manager.get_order_by_number(order_number)

def get_order_by_id(order_id: int, db_path: str = None) -> Optional[Dict]:
    """根据订单ID获取订单"""
    manager = OrderManager(db_path)
    return manager.get_order_by_id(order_id)

def search_orders(query: str, db_path: str = None) -> List[Dict]:
    """搜索订单"""
    manager = OrderManager(db_path)
    return manager.search_orders(query)

def get_all_orders(limit: int = 100, db_path: str = None) -> List[Dict]:
    """获取所有订单"""
    manager = OrderManager(db_path)
    return manager.get_all_orders(limit)

def update_order_number(order_id: int, new_order_number: str, db_path: str = None) -> bool:
    """更新订单编号"""
    manager = OrderManager(db_path)
    return manager.update_order_number(order_id, new_order_number)
