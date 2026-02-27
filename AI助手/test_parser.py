from shipment_parser import ShipmentParser

# 测试订单
order_text = '七彩乐园10桶9083规格28，PE白底稀释剂180kg1桶，PE哑光白面漆5桶规格28'

# 测试解析器
parser = ShipmentParser()

# 测试编号模式开启
result_number = parser.parse(order_text, number_mode=True)
print('编号模式开启:')
print('购买单位:', result_number.purchase_unit)
print('产品:')
for p in result_number.products:
    print('  ', p)

print('\n---\n')

# 测试编号模式关闭
result_no_number = parser.parse(order_text, number_mode=False)
print('编号模式关闭:')
print('购买单位:', result_no_number.purchase_unit)
print('产品:')
for p in result_no_number.products:
    print('  ', p)

print('\n---\n')

# 测试自定义模式
result_custom = parser.parse(order_text, custom_mode=True)
print('自定义模式:')
print('购买单位:', result_custom.purchase_unit)
print('产品:')
for p in result_custom.products:
    print('  ', p)
