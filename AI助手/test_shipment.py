import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser
from shipment_parser import ShipmentRecordManager

# 解析订单
parser = AIAugmentedShipmentParser()
test_input = "七彩乐园Pe白底漆10桶规格28, 哑光银珠1桶规格20Kg，PE白底漆稀料1桶规格180"
print(f"输入: {test_input}\n")

result = parser.parse(test_input)

print("=== 解析结果 ===")
print(f"购买单位: {result.purchase_unit}")
print(f"产品数量: {len(result.products)}\n")

for i, p in enumerate(result.products, 1):
    print(f"{i}. {p.get('name')} - {p.get('quantity_tins')}桶")

# 保存到出货记录
manager = ShipmentRecordManager()
record_id = manager.create_record(result, None)
print(f"\n=== 出货记录 ===")
print(f"保存成功，记录ID: {record_id}")

# 查询所有出货记录
print("\n所有出货记录:")
records = manager.get_all_records()
for r in records[-5:]:  # 显示最近5条
    print(f"  ID={r['id']}: {r['product_name']} - {r['quantity_tins']}桶")
