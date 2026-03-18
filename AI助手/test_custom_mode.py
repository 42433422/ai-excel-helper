#!/usr/bin/env python3

from shipment_document import DocumentAPIGenerator

# 创建文档生成器
api = DocumentAPIGenerator()

# 测试订单 - 用户提供的测试用例
order_text = '温总编号NC50F，NC哑光清面漆3桶规格25单价14.5'

# 使用自定义模式生成文档
result = api.parse_and_generate(order_text, custom_mode=True)

# 打印结果
if result['success']:
    print('成功')
    print(f'产品数量: {len(result["parsed_data"]["products"])} 个')
    for p in result['parsed_data']['products']:
        print(f'产品名称: {p["name"]}, 型号: {p["model_number"]}, 数量: {p["quantity_tins"]}桶, 规格: {p["tin_spec"]}kg, 单价: {p["unit_price"]}, 金额: {p["amount"]}')
else:
    print('失败')
    print(result['message'])