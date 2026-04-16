import subprocess
import sys

# 使用 pip 安装 pdfplumber
subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "-q"])

import pdfplumber
import os

# 列出所有 PDF 文件
pdf_path = r'E:\FHD\XCAGI\龙象 AI 方案 (文案).pdf'
print(f"检查文件：{pdf_path}")
print(f"文件存在：{os.path.exists(pdf_path)}")
print(f"文件大小：{os.path.getsize(pdf_path)} bytes")

# 打开 PDF
with pdfplumber.open(pdf_path) as pdf:
    print(f'\n总页数：{len(pdf.pages)}\n')
    
    # 提取前 15 页内容
    for i in range(min(15, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text()
        print(f'\n=== 第 {i+1} 页 ===')
        print(text[:4000] if text else '[无文本内容]')
