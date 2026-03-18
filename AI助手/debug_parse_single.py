#!/usr/bin/env python3

from shipment_parser import ShipmentParser

# 创建解析器
parser = ShipmentParser()

# 测试订单
order_text = '温总编号NC50F，测试专用产品3桶规格25单价14.5'

# 提取购买单位
purchase_unit = parser._extract_purchase_unit(order_text)
print(f'购买单位：{purchase_unit}')

# 分割产品
product_items = parser._split_products(order_text, purchase_unit)
print(f'产品项目：{product_items}')

# 解析单个产品
for item_text in product_items:
    item_text = item_text.replace('自定义', '').strip()
    print(f'\n解析产品：{item_text}')
    
    # 提取数量信息
    quantity_info = parser._extract_quantity(item_text)
    print(f'数量信息：{quantity_info}')
    
    # 提取单价信息
    unit_price = 0.0
    unit_price_match = parser._extract_quantity(item_text)
    print(f'单价匹配：{unit_price_match}')
    
    # 直接使用正则表达式提取
    import re
    unit_price_match = re.search(r'单价(\d+(?:\.\d+)?)', item_text)
    if unit_price_match:
        unit_price = float(unit_price_match.group(1))
        print(f'提取到单价：{unit_price}')
    
    # 提取规格信息
    tin_spec = 10.0
    if '规格' in item_text:
        spec_match = re.search(r'规格(\d+(?:\.\d+)?)', item_text)
        if spec_match:
            tin_spec = float(spec_match.group(1))
            print(f'提取到规格：{tin_spec}')
    
    # 提取型号
    model_match = re.search(r'(型号|编号)([A-Z0-9-]+)', order_text, re.IGNORECASE)
    if model_match:
        model_number = model_match.group(2)
        print(f'提取到型号：{model_number}')
    
    # 测试_parse_single_product方法
    product = parser._parse_single_product(item_text, is_custom=True)
    if product:
        print(f'最终产品：{product}')
    else:
        print('解析失败')