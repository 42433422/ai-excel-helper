import sqlite3
import sys

def analyze_database(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 分析products表结构
        if tables:
            for table in tables:
                table_name = table[0]
                print(f"\n{table_name}表结构:")
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
                
                # 获取数据样本
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                sample_data = cursor.fetchall()
                print(f"\n{table_name}表前5行数据:")
                for row in sample_data:
                    print(f"  {row}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"分析数据库时出错: {e}")
        return False

if __name__ == "__main__":
    db_path = "e:/FHD/424/半岛风情.db"
    print(f"正在分析数据库: {db_path}")
    success = analyze_database(db_path)
    if success:
        print("\n数据库分析完成!")
    else:
        print("\n数据库分析失败!")