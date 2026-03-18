import sys
sys.path.insert(0, '.')
from ocr_processor import OCRProcessor
import json

processor = OCRProcessor()
result = processor.process_image('10e0a348efcb5359614a60f1ea576df3.jpg')
print('识别结果:')
print(json.dumps(result, ensure_ascii=False, indent=2))
