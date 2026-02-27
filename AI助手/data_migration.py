#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本
将Excel文件中的数据映射并更新到数据库中
"""

import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import json

class DataMigration:
    """数据迁移类"""
    
    def __init__(self, excel_file, db_path):
        self.excel_file = excel_file
        self.db_path = db_path
        self.backup_path = db_path + '.backup'
        self.migration_results = {
            'total_records': 0,
            'processed_records': 0,
            'successful_updates': 0,
            'new_records': 0,
            'skipped_records': 0,
            'errors': [],
            'ruixin_records': 0
        }
        
    def backup_database(self):
        """备份数据库"""
        try:
            if os.path.exists(self.db_path):
                import shutil
                shutil.copy2(self.db_path, self.backup_path)
                print(f"✅ 数据库备份成功: {self.backup_path}")
                return True
            else:
                print(f"⚠️  数据库文件不存在: {self.db_path}")
                return False
        except Exception as e:
            print(f"❌ 备份失败: {e}")
            return False
    
    def get_ruixin_data(self):
        """获取蕊芯相关数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取蕊芯购买单位
        cursor.execute('SELECT * FROM purchase_units WHERE unit_name LIKE "%蕊芯%"')
        ruixin_units = cursor.fetchall()
        
        # 获取蕊芯相关的客户产品关联
        ruixin_unit_ids = [unit[0] for unit in ruixin_units]
        ruixin_products = []
        if ruixin_unit_ids:
            placeholders = ','.join(['?' for _ in ruixin_unit_ids])
            cursor.execute(f'SELECT * FROM customer_products WHERE unit_id IN ({placeholders})', ruixin_unit_ids)
            ruixin_products = cursor.fetchall()
        
        conn.close()
        
        return {
            'units': ruixin_units,
            'products': ruixin_products
        }
    
    def clear_non_ruixin_data(self):
        """清空除蕊芯外的所有数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取蕊芯购买单位ID
            cursor.execute('SELECT id FROM purchase_units WHERE unit_name LIKE "%蕊芯%"')
            ruixin_unit_ids = [row[0] for row in cursor.fetchall()]
            
            # 删除非蕊芯的客户产品关联
            if ruixin_unit_ids:
                placeholders = ','.join(['?' for _ in ruixin_unit_ids])
                cursor.execute(f'DELETE FROM customer_products WHERE unit_id NOT IN ({placeholders})', ruixin_unit_ids)
            else:
                cursor.execute('DELETE FROM customer_products')
            
            # 删除非蕊芯的购买单位
            if ruixin_unit_ids:
                placeholders = ','.join(['?' for _ in ruixin_unit_ids])
                cursor.execute(f'DELETE FROM purchase_units WHERE id NOT IN ({placeholders})', ruixin_unit_ids)
            else:
                cursor.execute('DELETE FROM purchase_units')
            
            # 删除所有产品（会被新数据替代）
            cursor.execute('DELETE FROM products')
            
            conn.commit()
            print(f"✅ 清空非蕊芯数据成功")
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ 清空数据失败: {e}")
            return False
        finally:
            conn.close()
    
    def process_excel_data(self):
        """处理Excel数据"""
        try:
            # 读取Excel文件
            df = pd.read_excel(self.excel_file, sheet_name='Sheet1')
            
            print(f"=== Excel数据处理 ===")
            print(f"原始数据行数: {len(df)}")
            self.migration_results['total_records'] = len(df)
            
            # 过滤无效数据
            df = df.dropna(subset=['购买单位', '产品名称'])
            print(f"过滤后数据行数: {len(df)}")
            
            # 按购买单位分组
            grouped = df.groupby('购买单位')
            print(f"购买单位数量: {len(grouped)}")
            
            processed_data = []
            
            # 处理每个购买单位的数据
            for unit_name, group in grouped:
                print(f"\n处理购买单位: {unit_name}")
                print(f"产品数量: {len(group)}")
                
                # 按型号和名称分组，保留最后一个
                unit_processed = self._process_unit_data(unit_name, group)
                processed_data.extend(unit_processed)
            
            print(f"\n=== 处理结果 ===")
            print(f"处理后总记录数: {len(processed_data)}")
            
            return processed_data
            
        except Exception as e:
            print(f"❌ 处理Excel数据失败: {e}")
            return []
    
    def _process_unit_data(self, unit_name, group):
        """处理单个购买单位的数据"""
        # 按型号和名称分组
        key_groups = {}
        
        for idx, row in group.iterrows():
            model_number = str(row.get('产品型号', '')).strip()
            product_name = str(row.get('产品名称', '')).strip()
            price = row.get('单价', 0.0)
            
            # 创建唯一键
            key = f"{model_number}_{product_name}"
            
            # 保留最后一个（最底下的）
            key_groups[key] = {
                'unit_name': unit_name,
                'model_number': self._normalize_model_number(model_number),
                'product_name': product_name,
                'price': price,
                'original_model': model_number
            }
        
        # 转换为列表
        processed = list(key_groups.values())
        print(f"去重后产品数量: {len(processed)}")
        
        return processed
    
    def _normalize_model_number(self, model_number):
        """规范化型号"""
        if not model_number:
            return ''
        
        # 移除括号内容
        model_number = re.sub(r'\([^)]*\)', '', model_number)
        
        # 清理空格
        model_number = model_number.strip()
        
        # 处理日期格式型号
        date_pattern = r'^(\d{4})([A-Za-z]?)$'
        match = re.match(date_pattern, model_number)
        if match:
            date_part = match.group(1)
            letter_part = match.group(2) or 'A'
            return f"{date_part}{letter_part}"
        
        return model_number
    
    def import_data(self, processed_data):
        """导入处理后的数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 导入购买单位
            unit_mapping = self._import_purchase_units(processed_data, cursor)
            
            # 导入产品
            product_mapping = self._import_products(processed_data, cursor)
            
            # 导入客户产品关联
            self._import_customer_products(processed_data, unit_mapping, product_mapping, cursor)
            
            conn.commit()
            print("✅ 数据导入成功")
            return True
        except Exception as e:
            conn.rollback()
            print(f"❌ 导入失败: {e}")
            return False
        finally:
            conn.close()
    
    def _import_purchase_units(self, processed_data, cursor):
        """导入购买单位"""
        unit_names = set()
        for item in processed_data:
            unit_names.add(item['unit_name'])
        
        unit_mapping = {}
        
        for unit_name in unit_names:
            # 检查是否已存在
            cursor.execute('SELECT id FROM purchase_units WHERE unit_name = ?', (unit_name,))
            existing = cursor.fetchone()
            
            if existing:
                unit_id = existing[0]
                print(f"ℹ️  购买单位已存在: {unit_name} (ID: {unit_id})")
            else:
                # 插入新购买单位
                cursor.execute('''
                INSERT INTO purchase_units (unit_name, is_active, created_at, updated_at)
                VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (unit_name,))
                unit_id = cursor.lastrowid
                print(f"➕ 新增购买单位: {unit_name} (ID: {unit_id})")
                self.migration_results['new_records'] += 1
            
            unit_mapping[unit_name] = unit_id
        
        return unit_mapping
    
    def _import_products(self, processed_data, cursor):
        """导入产品"""
        product_mapping = {}
        
        for item in processed_data:
            model_number = item['model_number']
            product_name = item['product_name']
            price = item['price']
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM products WHERE model_number = ? AND name = ?', (model_number, product_name))
            existing = cursor.fetchone()
            
            if existing:
                product_id = existing[0]
                # 更新价格
                cursor.execute('UPDATE products SET price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (price, product_id))
                print(f"ℹ️  更新产品价格: {product_name} (ID: {product_id}, 价格: {price})")
                self.migration_results['successful_updates'] += 1
            else:
                # 插入新产品
                try:
                    cursor.execute('''
                    INSERT INTO products (model_number, name, price, unit, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, '个', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (model_number, product_name, price))
                    product_id = cursor.lastrowid
                    print(f"➕ 新增产品: {product_name} (ID: {product_id})")
                    self.migration_results['new_records'] += 1
                except Exception as e:
                    print(f"❌ 插入产品失败: {product_name}, 型号: {model_number}, 错误: {e}")
                    self.migration_results['errors'].append(f"{product_name}: {e}")
                    continue
            
            key = f"{model_number}_{product_name}"
            product_mapping[key] = product_id
        
        return product_mapping
    
    def _import_customer_products(self, processed_data, unit_mapping, product_mapping, cursor):
        """导入客户产品关联"""
        for item in processed_data:
            unit_name = item['unit_name']
            model_number = item['model_number']
            product_name = item['product_name']
            price = item['price']
            
            unit_id = unit_mapping.get(unit_name)
            product_key = f"{model_number}_{product_name}"
            product_id = product_mapping.get(product_key)
            
            if unit_id and product_id:
                # 检查是否已存在
                cursor.execute('SELECT id FROM customer_products WHERE unit_id = ? AND product_id = ?', (unit_id, product_id))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新价格
                    cursor.execute('UPDATE customer_products SET custom_price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (price, existing[0]))
                else:
                    # 插入新关联
                    cursor.execute('''
                    INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (unit_id, product_id, price))
    
    def validate_migration(self):
        """验证迁移结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 统计数据
            cursor.execute('SELECT COUNT(*) FROM purchase_units')
            units_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM products')
            products_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM customer_products')
            customer_products_count = cursor.fetchone()[0]
            
            # 检查蕊芯数据是否保留
            cursor.execute('SELECT COUNT(*) FROM purchase_units WHERE unit_name LIKE "%蕊芯%"')
            ruixin_count = cursor.fetchone()[0]
            
            print(f"\n=== 验证结果 ===")
            print(f"购买单位数量: {units_count}")
            print(f"产品数量: {products_count}")
            print(f"客户产品关联数量: {customer_products_count}")
            print(f"蕊芯相关购买单位数量: {ruixin_count}")
            
            return {
                'units_count': units_count,
                'products_count': products_count,
                'customer_products_count': customer_products_count,
                'ruixin_count': ruixin_count
            }
        finally:
            conn.close()
    
    def generate_report(self):
        """生成迁移报告"""
        report = {
            'migration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'excel_file': self.excel_file,
            'database': self.db_path,
            'results': self.migration_results,
            'validation': self.validate_migration()
        }
        
        print(f"\n=== 数据迁移报告 ===")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        
        # 保存报告
        report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 报告已保存: {report_file}")
        
        return report
    
    def run(self):
        """执行完整的迁移流程"""
        print("=== 开始数据迁移 ===")
        
        # 1. 备份数据库
        if not self.backup_database():
            print("❌ 备份失败，终止迁移")
            return False
        
        # 2. 获取蕊芯数据
        ruixin_data = self.get_ruixin_data()
        print(f"✅ 已获取蕊芯数据: {len(ruixin_data['units'])}个单位, {len(ruixin_data['products'])}个产品关联")
        
        # 3. 清空非蕊芯数据
        if not self.clear_non_ruixin_data():
            print("❌ 清空数据失败，终止迁移")
            return False
        
        # 4. 处理Excel数据
        processed_data = self.process_excel_data()
        if not processed_data:
            print("❌ 处理Excel数据失败，终止迁移")
            return False
        
        # 5. 导入数据
        if not self.import_data(processed_data):
            print("❌ 导入数据失败")
            return False
        
        # 6. 生成报告
        self.generate_report()
        
        print("\n=== 数据迁移完成 ===")
        return True

if __name__ == "__main__":
    # 配置
    excel_file = "新建 XLSX 工作表 (2).xlsx"
    db_path = "products.db"
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel文件不存在: {excel_file}")
        exit(1)
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        exit(1)
    
    # 执行迁移
    migration = DataMigration(excel_file, db_path)
    success = migration.run()
    
    if success:
        print("🎉 数据迁移成功！")
    else:
        print("💥 数据迁移失败！")
