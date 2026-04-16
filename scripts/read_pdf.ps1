# 使用 PowerShell 和 Python 读取 PDF

# 1. 首先确认文件
$pdfFile = "E:\FHD\XCAGI\龙象 AI 方案 (文案).pdf"
Write-Host "文件路径：$pdfFile"
Write-Host "文件存在：$(Test-Path $pdfFile)"

# 2. 复制到临时位置 (使用短路径)
$tempPdf = "C:\temp\longxiang.pdf"
if (Test-Path "C:\temp") {
    Copy-Item $pdfFile $tempPdf -Force
    Write-Host "已复制到：$tempPdf"
    
    # 3. 使用 Python 读取
    $pythonScript = @"
import pdfplumber
import os

pdf_path = r'$tempPdf'
print(f"文件大小：{os.path.getsize(pdf_path)} bytes")

with pdfplumber.open(pdf_path) as pdf:
    print(f'总页数：{len(pdf.pages)}\n')
    
    for i in range(min(20, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text()
        print(f'\n=== 第 {i+1} 页 ===')
        if text:
            print(text[:5000])
        else:
            print('[无文本内容]')
"@
    
    python -c "$pythonScript"
} else {
    Write-Host "C:\temp 目录不存在"
}
