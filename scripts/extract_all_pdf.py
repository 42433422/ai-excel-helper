import fitz
import glob

# 找到 PDF 文件
pdf_file = glob.glob('E:/FHD/XCAGI/*.pdf')[0]

# 打开 PDF
doc = fitz.open(pdf_file)

# 提取所有页面内容
all_text = []
for i in range(len(doc)):
    text = doc[i].get_text()
    all_text.append(text)
    print(f"\n=== 第 {i+1} 页 ===")
    print(text if text else '[无文本]')

doc.close()

# 保存为文本文件
with open('E:/FHD/longxiang_content.txt', 'w', encoding='utf-8') as f:
    for i, text in enumerate(all_text):
        f.write(f"\n\n=== 第 {i+1} 页 ===\n")
        f.write(text if text else '[无文本]\n')

print("\n\n内容已保存到：E:/FHD/longxiang_content.txt")
