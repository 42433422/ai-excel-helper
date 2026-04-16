from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
import glob
import pprint

# 初始化 PaddleOCR (使用新 API)
ocr = PaddleOCR(lang='ch')

# 使用 glob 匹配
png_files = glob.glob(r"E:\FHD\*PE*.png")
print(f"找到文件：{png_files[0]}")

img_path = png_files[0]

# 读取图片
img = Image.open(img_path)
img_array = np.array(img)

print(f"图片尺寸：{img.size[0]} x {img.size[1]}")
print("=" * 50)

# 使用 predict 方法
result = ocr.predict(img_array)

print("\n=== PaddleOCR 识别结果 ===")
print(f"结果类型：{type(result)}")

# 打印 rec_texts 和 rec_scores
if isinstance(result, dict):
    rec_texts = result.get('rec_texts', [])
    rec_scores = result.get('rec_scores', [])
    
    print(f"\n共识别到 {len(rec_texts)} 个字段\n")
    
    for i, (text, score) in enumerate(zip(rec_texts, rec_scores), 1):
        print(f"{i}. {text} (置信度：{score:.4f})")
else:
    print("完整结果:")
    pprint.pprint(result)
