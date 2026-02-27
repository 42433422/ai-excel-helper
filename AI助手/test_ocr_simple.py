import cv2
import numpy as np
import re

# 读取图片
image_path = '10e0a348efcb5359614a60f1ea576df3.jpg'
image = cv2.imread(image_path)

if image is None:
    print("无法读取图片")
    exit()

print(f"图片尺寸: {image.shape}")

# 调整图片大小
height, width = image.shape[:2]
target_size = 1500
if max(height, width) > target_size:
    scale = target_size / max(height, width)
    image = cv2.resize(image, None, fx=scale, fy=scale)
    print(f"调整后尺寸: {image.shape}")

# 保存处理后的图片用于测试
cv2.imwrite('test_processed.jpg', image)
print("处理后的图片已保存为 test_processed.jpg")

# 尝试使用easyocr
try:
    import easyocr
    print("正在初始化EasyOCR...")
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=True)
    print("EasyOCR初始化成功")
    
    print("正在识别图片...")
    results = reader.readtext(image, detail=1)
    print(f"识别到 {len(results)} 个文本区域")
    
    for i, (bbox, text, confidence) in enumerate(results):
        print(f"{i+1}. {text} (置信度: {confidence:.2f})")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
