import sys
sys.path.insert(0, '.')
from ocr_processor import OCRProcessor
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("="*60)
print("测试硅基流动视觉大模型OCR")
print("="*60)

processor = OCRProcessor()

print("\n测试图片: 10e0a348efcb5359614a60f1ea576df3.jpg")
print("-"*60)

result = processor.process_image('10e0a348efcb5359614a60f1ea576df3.jpg')

print('\n识别结果:')
print(json.dumps(result, ensure_ascii=False, indent=2))

# 生成订单文本
if result['customer'] or result['products']:
    order_text = result['customer'] if result['customer'] else ""
    
    product_texts = []
    for p in result['products']:
        text = p.get('name', '')
        if p.get('quantity'):
            text += p['quantity'] + '桶'
        if p.get('spec'):
            text += '规格' + p['spec']
        product_texts.append(text)
    
    if product_texts:
        if order_text:
            order_text += '，'
        order_text += '，'.join(product_texts)
    
    print('\n生成的订单文本:')
    print(order_text)
