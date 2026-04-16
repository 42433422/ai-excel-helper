import fitz
import os

# 使用短路径和简单的文件名
pdf_path = r'E:/FHD/XCAGI/longxiang_copy.pdf'

# 首先复制文件
import shutil
source = 'E:/FHD/XCAGI/龙象 AI 方案 (文案).pdf'
dest = 'E:/FHD/XCAGI/longxiang_copy.pdf'

try:
    shutil.copy2(source, dest)
    print(f"文件已复制：{dest}")
    print(f"文件大小：{os.path.getsize(dest)}")
except Exception as e:
    print(f"复制失败：{e}")
    # 尝试直接列出目录
    print("\nXCAGI 目录中的 PDF 文件:")
    xcagi_dir = 'E:/FHD/XCAGI'
    for f in os.listdir(xcagi_dir):
        if f.endswith('.pdf'):
            print(f"  {f} - {os.path.getsize(os.path.join(xcagi_dir, f))} bytes")
