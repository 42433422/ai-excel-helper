import sqlite3
import os

def check_customer_databases():
    """检查客户相关的数据库"""
    
    # 检查customers.db
    print("=== 检查 customers.db ===")
    try:
        conn = sqlite3.connect('e:/FHD/424/customers.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("表列表:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print("    列结构:")
            for col in columns:
                print(f"      {col[1]} ({col[2]})")
            
            # 检查是否有'半岛风情'相关数据
            cursor.execute(f"SELECT * FROM {table[0]} WHERE name LIKE '%半岛%' OR name LIKE '%风情%'")
            results = cursor.fetchall()
            if results:
                print(f"    找到'半岛风情'相关数据: {len(results)} 条")
                for row in results:
                    print(f"      {row}")
            else:
                print("    未找到'半岛风情'相关数据")
                
        conn.close()
    except Exception as e:
        print(f"检查customers.db时出错: {e}")
    
    print("\n=== 检查 database.db ===")
    try:
        conn = sqlite3.connect('e:/FHD/424/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("表列表:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print("    列结构:")
            for col in columns:
                print(f"      {col[1]} ({col[2]})")
            
            # 检查是否有'半岛风情'相关数据
            cursor.execute(f"SELECT * FROM {table[0]} WHERE name LIKE '%半岛%' OR name LIKE '%风情%'")
            results = cursor.fetchall()
            if results:
                print(f"    找到'半岛风情'相关数据: {len(results)} 条")
                for row in results:
                    print(f"      {row}")
            else:
                print("    未找到'半岛风情'相关数据")
                
        conn.close()
    except Exception as e:
        print(f"检查database.db时出错: {e}")

if __name__ == "__main__":
    check_customer_databases()