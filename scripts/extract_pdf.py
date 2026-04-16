import fitz
import os
import glob

# 列出所有 PDF 文件
pdf_files = glob.glob('E:/FHD/XCAGI/*.pdf')
print("找到的 PDF 文件:")
for f in pdf_files:
    print(f"  {f}")
    if '龙象' in f or 'longxiang' in f.lower():
        print(f"    -> 这就是目标文件!")
        
        # 尝试打开
        try:
            doc = fitz.open(f)
            print(f"    总页数：{len(doc)}")
            print(f"    元数据：{doc.metadata}")
            
            # 提取前 10 页
            for i in range(min(10, len(doc))):
                text = doc[i].get_text()
                print(f"\n=== 第 {i+1} 页 ===")
                print(text[:5000] if text else '[无文本]')
            doc.close()
        except Exception as e:
            print(f"    打开失败：{e}")
