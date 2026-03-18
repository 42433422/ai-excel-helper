#!/usr/bin/env python3
# 测试脚本，模拟API的行为
import sys
import os
import urllib.parse
import sqlite3

def test_get_products(unit):
    print(f"测试单位: {unit}")
    
    # 模拟API的路径构建
    current_dir = os.path.dirname(os.path.abspath('app_api.py'))
    print(f"当前目录: {current_dir}")
    
    # 手动解码URL编码的单位名称
    unit = urllib.parse.unquote(unit)
    print(f"解码后单位: {unit}")
    
    db_path = os.path.join(current_dir, 'unit_databases', f'{unit}.db')
    print(f"数据库路径: {db_path}")
    print(f"文件是否存在: {os.path.exists(db_path)}")
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查数据库中的表
            cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = cursor.fetchall()
            print(f"数据库中的表: {[t[0] for t in tables]}")
            
            # 检查products表
            cursor.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]
            print(f"Products表记录数: {count}")
            
            # 测试查询
            cursor.execute('''
                SELECT id, model_number, name, specification, price, quantity, description
                FROM products 
                ORDER BY name
                LIMIT 3
            ''')
            products = cursor.fetchall()
            print(f"查询到的产品数: {len(products)}")
            
            if products:
                print("前3个产品:")
                for i, product in enumerate(products):
                    print(f"  {i+1}. ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"错误: {e}")
            return False
    else:
        print("数据库文件不存在")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python test_api_behavior.py <单位名称>")
        sys.exit(1)
    
    unit = sys.argv[1]
    success = test_get_products(unit)
    print(f"测试结果: {'成功' if success else '失败'}")