# -*- coding: utf-8 -*-
import requests
import os

# 图片路径
image_path = r'c:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手\10e0a348efcb5359614a60f1ea576df3.jpg'

# API 端点
url = 'http://127.0.0.1:5000/api/ocr/process-image'

# 发送图片进行 OCR 识别
with open(image_path, 'rb') as f:
    files = {'image': f}
    try:
        response = requests.post(url, files=files, timeout=60)
        print('=== OCR API 响应 ===')
        print(response.json())
    except Exception as e:
        print(f'调用失败: {e}')
