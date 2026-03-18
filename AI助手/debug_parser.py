from shipment_parser import ShipmentParser

# 测试订单
order_text = '七彩乐园10桶9083规格28，PE白底稀释剂180kg1桶，PE哑光白面漆5桶规格28'

# 测试解析器
parser = ShipmentParser()

# 查看内部处理过程
print('=== 调试信息 ===')

# 提取购买单位
purchase_unit = parser._extract_purchase_unit(order_text)
print(f'购买单位: {purchase_unit}')

# 分割产品
product_items = parser._split_products(order_text, purchase_unit)
print(f'分割后的产品项: {product_items}')

# 解析每个产品
for i, item in enumerate(product_items):
    print(f'\n--- 产品 {i+1}: {item} ---')
    
    # 编号模式处理
    print('编号模式处理:')
    # 模拟 _match_product_from_db 的清理过程
    import re
    search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', item)
    # 编号模式下保留数字
    number_mode = True
    if not number_mode:
        search_text = re.sub(r'\d+(?:\.\d+)?', '', search_text)
    # 移除购买单位
    if purchase_unit:
        search_text = search_text.replace(purchase_unit, '').strip()
    print(f'清理后的文本: {search_text}')
    
    # 提取关键词
    keywords = parser._extract_product_keywords(search_text)
    print(f'提取的关键词: {keywords}')

print('\n=== 测试完成 ===')
