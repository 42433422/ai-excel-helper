# -*- coding: utf-8 -*-
import sys
import os

# 添加正确的路径
ai_path = r'c:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手'
sys.path.insert(0, ai_path)
sys.path.insert(0, os.path.join(ai_path, 'BarTender_Template_Tools'))

from bartender_ocr_backend import OCRTextProcessor
from PIL import Image

proc = OCRTextProcessor()
img = Image.open(os.path.join(ai_path, '10e0a348efcb5359614a60f1ea576df3.jpg'))

print("=== 图片尺寸 ===")
print(f"宽度: {img.size[0]}, 高度: {img.size[1]}")

print("\n=== EasyOCR 识别结果 ===")
result = proc.recognize_text(img)

for item in result:
    print(f"文字: {item['text']} | 置信度: {item['confidence']:.2f} | 位置: ({item['x']}, {item['y']})")
