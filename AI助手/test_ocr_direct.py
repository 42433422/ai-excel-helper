import sys
sys.path.insert(0, '.')
from ocr_processor import OCRProcessor
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("正在初始化OCR处理器...")
processor = OCRProcessor()

print("正在处理图片...")
result = processor.process_image('10e0a348efcb5359614a60f1ea576df3.jpg')

print('\n识别结果:')
print(json.dumps(result, ensure_ascii=False, indent=2))
