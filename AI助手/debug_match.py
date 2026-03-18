import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

# 创建解析器
parser = AIAugmentedShipmentParser()

# 检查七彩乐园数据库中的所有产品
db_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/unit_databases/七彩乐园.db"

import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT id, name, model_number FROM products WHERE name LIKE '%PE%' OR name LIKE '%白底%'")
products = cursor.fetchall()
conn.close()

print("=== 七彩乐园中包含 PE 或 白底 的产品 ===\n")
for p in products:
    print(f"ID: {p[0]}, 名称: {p[1]}, 型号: {p[2]}")

print("\n=== 调试匹配逻辑 ===\n")

# 手动测试匹配
search_text = "PE白底稀释剂"
print(f"搜索: {search_text}\n")

# 检查是否匹配到 PE白底漆稀料
for p in products:
    name = p[1].lower()
    if "pe" in name and "底" in name:
        print(f"检查产品: {p[1]}")
        print(f"  'PE' in search: {'PE' in search_text}")
        print(f"  'PE' in name: {'PE' in name}")
        print(f"  '稀释剂' in search: {'稀释剂' in search_text}")
        print(f"  '稀料' in name: {'稀料' in name}")
        print()
