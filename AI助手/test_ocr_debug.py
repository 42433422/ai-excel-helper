import sys
sys.path.insert(0, '.')
from ocr_processor import OCRProcessor
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("="*60)
print("测试图片1: 10e0a348efcb5359614a60f1ea576df3.jpg (填写完成的凭证)")
print("="*60)

processor = OCRProcessor()
result1 = processor.process_image('10e0a348efcb5359614a60f1ea576df3.jpg')

print('\n识别结果:')
print(json.dumps(result1, ensure_ascii=False, indent=2))

print("\n" + "="*60)
print("测试图片2: a7fe49666566d0b5f519b97511f58c4c.jpg (空白模板)")
print("="*60)

result2 = processor.process_image('a7fe49666566d0b5f519b97511f58c4c.jpg')

print('\n识别结果:')
print(json.dumps(result2, ensure_ascii=False, indent=2))
