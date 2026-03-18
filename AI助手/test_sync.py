import requests
import json

# 测试生成发货单并同步到Excel
url = "http://127.0.0.1:5000/api/generate"
data = {
    "order_text": "七彩乐园PE白底漆10桶规格28",
    "template_name": "尹玉华1.xlsx",
    "excel_sync": True
}

print("=== 测试生成发货单并同步到Excel ===\n")
print(f"订单: {data['order_text']}")
print(f"Excel同步: {data['excel_sync']}\n")

try:
    response = requests.post(url, json=data, timeout=30)
    result = response.json()
    
    print(f"状态: {'成功' if result.get('success') else '失败'}")
    print(f"消息: {result.get('message', '')}\n")
    
    if result.get('success'):
        doc = result.get('document', {})
        print(f"发货单文件: {doc.get('filename', 'N/A')}")
        print(f"\n解析数据:")
        parsed = result.get('parsed_data', {})
        print(f"  购买单位: {parsed.get('purchase_unit', 'N/A')}")
        print(f"  产品名称: {parsed.get('product_name', 'N/A')}")
        print(f"  型号: {parsed.get('model_number', 'N/A')}")
        print(f"  数量: {parsed.get('quantity_kg', 0)}kg")
        print(f"  桶数: {parsed.get('quantity_tins', 0)}桶")
        print(f"  桶规格: {parsed.get('tin_spec', 0)}kg/桶")
        print(f"  单价: {parsed.get('unit_price', 0)}")
        print(f"  金额: {parsed.get('amount', 0)}")
        
        excel_sync = result.get('excel_sync', {})
        print(f"\nExcel同步:")
        print(f"  启用: {excel_sync.get('enabled', False)}")
        print(f"  成功: {excel_sync.get('success', False)}")
        if excel_sync.get('error'):
            print(f"  错误: {excel_sync.get('error')}")
    else:
        print(f"错误: {result.get('message', '未知错误')}")
        
except Exception as e:
    print(f"请求失败: {e}")
