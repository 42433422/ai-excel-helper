import sqlite3
from datetime import datetime

# 测试数据库连接和查询
try:
    print("开始测试数据库连接...")
    
    # 连接到数据库
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    print("✅ 数据库连接成功")
    
    # 检查orders表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders';")
    orders_table_exists = cursor.fetchone() is not None
    print(f"✅ orders表存在: {orders_table_exists}")
    
    # 检查表结构
    if orders_table_exists:
        print("\norders表结构:")
        cursor.execute("PRAGMA table_info(orders);")
        for row in cursor.fetchall():
            print(row)
    
    # 尝试获取最新订单
    print("\n尝试获取最新订单...")
    cursor.execute("""
        SELECT order_number, created_at FROM orders 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    latest_order = cursor.fetchone()
    print(f"✅ 最新订单: {latest_order}")
    
    # 生成当前年月和序列
    today = datetime.now()
    year = today.strftime("%y")
    month = today.strftime("%m")
    year_month = f"{year}-{month}"
    
    if latest_order:
        latest_order_number = latest_order[0]
        # 提取序列部分
        sequence_match = latest_order_number.split('-')[2].split('A')[0]
        sequence = int(sequence_match) if sequence_match.isdigit() else 1
    else:
        latest_order_number = f"{year}-{month}-00001A"
        sequence = 1
    
    # 计算下一个序列
    next_sequence = sequence + 1
    next_order_number = f"{year}-{month}-{next_sequence:05d}A"
    
    print(f"\n订单编号信息:")
    print(f"  最新订单编号: {latest_order_number}")
    print(f"  下一个订单编号: {next_order_number}")
    print(f"  序列: {sequence}")
    print(f"  下一个序列: {next_sequence}")
    print(f"  年月: {year_month}")
    
    conn.close()
    print("\n✅ 测试完成，数据库操作正常")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()