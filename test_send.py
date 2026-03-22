# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-cv')

from resources.wechat_cv.wechat_cv_send import search_and_send_by_cv

result = search_and_send_by_cv("印记", "测试消息！你好", delay=1.0, use_ocr=True)
print(f"Result: {result}")