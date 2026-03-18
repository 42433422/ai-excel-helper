from shipment_parser import ShipmentParser

# 测试订单
order_text = '七彩乐园10桶9803规格28，PE白底稀释剂180kg1桶，PE哑光白面漆5桶规格28'

# 测试解析器
print('=== 初始化解析器 ===')
parser = ShipmentParser()

print('\n=== 测试完整解析 ===')
# 手动调用匹配方法
from shipment_parser import ShipmentParser

# 测试单个产品匹配
print('\n=== 测试单个产品匹配 ===')
# 测试PE白底稀释剂
result = parser._match_product_from_db('PE白底稀释剂180kg1桶', '七彩乐园', number_mode=True)
print('PE白底稀释剂匹配结果:', result)

# 测试9803
result = parser._match_product_from_db('10桶9803规格28', '七彩乐园', number_mode=True)
print('9803匹配结果:', result)

# 测试PE哑光白面漆
result = parser._match_product_from_db('PE哑光白面漆5桶规格28', '七彩乐园', number_mode=True)
print('PE哑光白面漆匹配结果:', result)

# 测试完整解析
print('\n=== 测试完整解析 ===')
result = parser.parse(order_text, number_mode=True)
print('购买单位:', result.purchase_unit)
print('产品:')
for p in result.products:
    print('  ', p)
