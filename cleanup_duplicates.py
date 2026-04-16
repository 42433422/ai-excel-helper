"""
清理重复产品记录
保留使用标准半角字符 (/) 的记录，删除使用全角字符 (／) 的重复记录
"""
import sqlite3

db_path = 'e:/FHD/424/products.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== 清理重复产品记录 ===\n")

# 查找所有重复的产品（按名称和型号分组）
cur.execute("""
    SELECT model_number, specification, COUNT(*) as cnt
    FROM products
    GROUP BY model_number, specification
    HAVING cnt > 1
""")
duplicates = cur.fetchall()

if not duplicates:
    print("未发现重复记录")
else:
    print(f"发现 {len(duplicates)} 组重复记录：")
    for dup in duplicates:
        print(f"  型号：{dup[0]}, 规格：{dup[1]}, 数量：{dup[2]}")

# 清理策略：保留半角字符 (/) 的记录，删除全角字符 (／) 的记录
print("\n=== 执行清理 ===")

# 找出需要删除的记录（使用全角字符的重复记录）
cur.execute("""
    SELECT id, model_number, specification
    FROM products
    WHERE specification LIKE '%／%'
    AND model_number IN (
        SELECT model_number 
        FROM products 
        WHERE specification LIKE '%/%'
    )
""")
to_delete = cur.fetchall()

if to_delete:
    print(f"将要删除 {len(to_delete)} 条使用全角字符的重复记录：")
    for row in to_delete:
        print(f"  ID: {row[0]}, 型号：{row[1]}, 规格：{row[2]}")
    
    # 确认删除
    confirm = input("\n确认删除这些记录吗？(yes/no): ")
    if confirm.lower() == 'yes':
        ids_to_delete = [row[0] for row in to_delete]
        placeholders = ','.join('?' * len(ids_to_delete))
        cur.execute(f"DELETE FROM products WHERE id IN ({placeholders})", ids_to_delete)
        conn.commit()
        print(f"✓ 已删除 {len(to_delete)} 条记录")
    else:
        print("取消删除")
else:
    print("没有需要删除的重复记录")

# 验证清理结果
print("\n=== 验证清理结果 ===")
cur.execute("SELECT model_number, specification, COUNT(*) as cnt FROM products GROUP BY model_number, specification HAVING cnt > 1")
remaining_duplicates = cur.fetchall()

if remaining_duplicates:
    print(f"仍发现 {len(remaining_duplicates)} 组重复记录：")
    for dup in remaining_duplicates:
        print(f"  型号：{dup[0]}, 规格：{dup[1]}, 数量：{dup[2]}")
else:
    print("✓ 所有重复记录已清理完毕")

# 显示清理后的产品
print("\n=== 清理后的产品记录 ===")
cur.execute("SELECT id, name, model_number, specification, price FROM products WHERE model_number IN ('3721', '1870D', '8828') ORDER BY model_number")
for row in cur.fetchall():
    print(f"ID: {row[0]}, 名称：{row[1]}, 型号：{row[2]}, 规格：{row[3]}, 价格：{row[4]}")

conn.close()
