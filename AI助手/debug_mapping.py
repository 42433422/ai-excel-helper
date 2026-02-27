import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

# 创建解析器
parser = AIAugmentedShipmentParser()

# 测试映射表
search_text = "PE白底稀释剂"
print(f"搜索文本: {search_text}\n")

# 检查映射表
product_type_mapping = {
    '白底漆稀释剂': ['PE白底漆稀释剂', '白底漆稀释剂', 'PE白底漆稀料', 'PE白底稀释剂'],
    'PU稀释剂': ['PU净味面漆稀释剂', 'PU稀释剂'],
    'PE稀释剂': ['PE稀释剂', 'PE稀料'],
}

print("=== 检查映射表匹配 ===\n")
for mapped_term, product_types in product_type_mapping.items():
    if mapped_term in search_text.lower():
        print(f"找到匹配: '{mapped_term}' in '{search_text.lower()}'")
        print(f"  对应的产品类型: {product_types}")
        
        # 检查数据库中是否有这些产品
        import sqlite3
        db_path = "c:/Users/97088/Desktop/新建文件夹 (4)/AI助手/unit_databases/七彩乐园.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for pt in product_types:
            cursor.execute("SELECT id, name, model_number FROM products WHERE name LIKE ?", (f'%{pt}%',))
            results = cursor.fetchall()
            if results:
                print(f"  数据库中找到 '{pt}':")
                for r in results:
                    print(f"    - {r[1]} (型号: {r[2]})")
        
        conn.close()
        print()

# 直接测试搜索
print("=== 直接测试 _match_product_from_db ===\n")
result = parser._match_product_from_db(search_text, "七彩乐园", False)
if result:
    print(f"匹配结果: {result['name']} (型号: {result['model_number']})")
else:
    print("未匹配到产品")
