#!/usr/bin/env python3
# 检查数据库中是否存在特定产品编号

import sqlite3
import os

def check_product_number():
    """检查数据库中是否存在特定产品编号"""
    print("=== 检查数据库中的产品编号 ===")
    
    # 获取数据库路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'products.db')
    
    print(f"数据库路径: {db_path}")
    print(f"数据库是否存在: {os.path.exists(db_path)}")
    print()
    
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 检查所有产品表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")
        print()
        
        # 2. 检查products表结构和数据
        try:
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]
            print(f"products表中的产品数量: {product_count}")
            
            # 显示products表结构
            cursor.execute("PRAGMA table_info(products)")
            columns = cursor.fetchall()
            print("products表结构:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            print()
            
            # 3. 搜索包含"24"的产品
            print("搜索包含'24'的产品编号:")
            cursor.execute("SELECT id, model_number, name FROM products WHERE model_number LIKE '%24%' LIMIT 10")
            products_24 = cursor.fetchall()
            if products_24:
                for product in products_24:
                    print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
            else:
                print("  没有找到包含'24'的产品")
            print()
            
            # 4. 搜索包含"4-8"的产品
            print("搜索包含'4-8'的产品编号:")
            cursor.execute("SELECT id, model_number, name FROM products WHERE model_number LIKE '%4-8%'")
            products_4_8 = cursor.fetchall()
            if products_4_8:
                for product in products_4_8:
                    print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
            else:
                print("  没有找到包含'4-8'的产品")
            print()
            
            # 5. 搜索包含"24-4-8"的产品
            print("搜索包含'24-4-8'的产品编号:")
            cursor.execute("SELECT id, model_number, name FROM products WHERE model_number LIKE '%24-4-8%'")
            products_24_4_8 = cursor.fetchall()
            if products_24_4_8:
                for product in products_24_4_8:
                    print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
            else:
                print("  ❌ 没有找到包含'24-4-8'的产品编号")
            print()
            
            # 6. 显示一些示例产品编号
            print("数据库中的前10个产品编号示例:")
            cursor.execute("SELECT id, model_number, name FROM products LIMIT 10")
            sample_products = cursor.fetchall()
            for product in sample_products:
                print(f"  ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}")
            print()
            
        except Exception as e:
            print(f"查询products表时出错: {e}")
        
        # 7. 检查customer_products表
        try:
            print("检查customer_products表:")
            cursor.execute("SELECT COUNT(*) FROM customer_products")
            cp_count = cursor.fetchone()[0]
            print(f"customer_products表中的记录数量: {cp_count}")
            
            # 搜索客户专属产品中的"24-4-8"
            cursor.execute("""
                SELECT cp.id, p.model_number, p.name, c.客户名称, cp.custom_price
                FROM customer_products cp
                JOIN products p ON cp.product_id = p.id
                JOIN customers c ON cp.customer_id = c.id
                WHERE p.model_number LIKE '%24-4-8%'
                LIMIT 5
            """)
            cp_products = cursor.fetchall()
            if cp_products:
                print("客户专属产品中包含'24-4-8'的:")
                for product in cp_products:
                    print(f"  记录ID: {product[0]}, 型号: {product[1]}, 名称: {product[2]}, 客户: {product[3]}, 价格: {product[4]}")
            else:
                print("  ❌ 客户专属产品中也没有找到包含'24-4-8'的产品")
                
        except Exception as e:
            print(f"查询customer_products表时出错: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"数据库连接错误: {e}")

if __name__ == "__main__":
    check_product_number()