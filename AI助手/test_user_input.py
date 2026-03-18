import sys
sys.path.insert(0, '.')
from ai_augmented_parser import AIAugmentedShipmentParser

parser = AIAugmentedShipmentParser()

# 测试用户实际输入
test_input = "七彩乐园Pe白底漆10桶规格28, 哑光银珠1桶规格20Kg，PE白底漆稀料1桶规格180"
print(f"输入: {test_input}\n")

result = parser.parse(test_input)

print(f"购买单位: {result.purchase_unit}")
print(f"产品数量: {len(result.products)}\n")

for i, p in enumerate(result.products, 1):
    print(f"{i}. {p.get('name')} - {p.get('quantity_tins')}桶 (型号: {p.get('model_number')})")
