import markdown
import weasyprint
from weasyprint import CSS

md_path = r'e:\FHD\XCAGI\AI企业解决方案对比分析报告.md'
pdf_path = r'e:\FHD\XCAGI\AI企业解决方案对比分析报告.pdf'

# 读取 Markdown 文件
with open(md_path, 'r', encoding='utf-8') as f:
    md_content = f.read()

# 转换为 HTML
html_content = markdown.markdown(md_content)

# 现代 CSS 样式
css = CSS(string="""
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
    
    :root {
        --primary-color: #3498db;
        --secondary-color: #2c3e50;
        --accent-color: #e74c3c;
        --background-color: #f8f9fa;
        --card-color: #ffffff;
        --text-color: #333333;
        --border-color: #e0e0e0;
        --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    body {
        font-family: 'Noto Sans SC', sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: var(--text-color);
        background-color: var(--background-color);
        margin: 0;
        padding: 0;
    }
    
    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 40px;
        background-color: var(--card-color);
        box-shadow: var(--shadow);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Noto Sans SC', sans-serif;
        color: var(--secondary-color);
        margin-top: 1.5em;
        margin-bottom: 0.8em;
    }
    
    h1 {
        font-size: 28px;
        font-weight: 700;
        color: var(--primary-color);
        border-bottom: 3px solid var(--primary-color);
        padding-bottom: 10px;
        margin-bottom: 30px;
    }
    
    h2 {
        font-size: 22px;
        font-weight: 600;
        border-left: 4px solid var(--primary-color);
        padding-left: 15px;
    }
    
    h3 {
        font-size: 18px;
        font-weight: 500;
        color: var(--secondary-color);
    }
    
    p {
        margin-bottom: 16px;
        text-align: justify;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        box-shadow: var(--shadow);
        border-radius: 8px;
        overflow: hidden;
    }
    
    th, td {
        padding: 12px 15px;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
    }
    
    th {
        background-color: var(--primary-color);
        color: white;
        font-weight: 500;
    }
    
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    
    tr:hover {
        background-color: #e3f2fd;
    }
    
    code {
        font-family: 'Courier New', monospace;
        background-color: #f1f1f1;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9em;
    }
    
    pre {
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 8px;
        overflow-x: auto;
        border-left: 4px solid var(--primary-color);
    }
    
    blockquote {
        border-left: 4px solid var(--primary-color);
        padding: 10px 20px;
        background-color: #f8f9fa;
        margin: 20px 0;
        border-radius: 0 8px 8px 0;
    }
    
    hr {
        border: none;
        border-top: 2px dashed var(--border-color);
        margin: 30px 0;
    }
    
    .footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid var(--border-color);
        text-align: center;
        color: #666;
        font-size: 12px;
    }
""")

# 包装 HTML
full_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 企业解决方案对比分析报告</title>
</head>
<body>
    <div class="container">
        {html_content}
        <div class="footer">
            <p>生成时间：2026-04-02</p>
        </div>
    </div>
</body>
</html>
"""

# 生成 PDF
try:
    html = weasyprint.HTML(string=full_html)
    pdf = html.write_pdf(stylesheets=[css])
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf)
    
    print(f'现代风格 PDF 生成成功: {pdf_path}')
except Exception as e:
    print(f'WeasyPrint 生成失败，使用备用方案: {e}')
    
    # 备用方案：使用 ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    
    # 注册中文字体
    pdfmetrics.registerFont(TTFont('SimHei', 'C:\\Windows\\Fonts\\simhei.ttf'))
    
    # 创建 PDF 文档
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    
    # 定义样式
    styles = getSampleStyleSheet()
    
    # 现代样式
    ModernStyle = ParagraphStyle(
        'Modern',
        fontName='SimHei',
        fontSize=12,
        leading=18,
        spaceAfter=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#333333')
    )
    
    ModernHeading1 = ParagraphStyle(
        'ModernHeading1',
        fontName='SimHei',
        fontSize=24,
        leading=30,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#3498db'),
        borderColor=colors.HexColor('#3498db'),
        borderWidth=2,
        borderPadding=10,
        backColor=colors.HexColor('#f8f9fa')
    )
    
    ModernHeading2 = ParagraphStyle(
        'ModernHeading2',
        fontName='SimHei',
        fontSize=18,
        leading=24,
        spaceAfter=15,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#2c3e50'),
        leftIndent=20,
        borderLeftWidth=4,
        borderLeftColor=colors.HexColor('#3498db')
    )
    
    # 构建内容
    story = []
    
    # 添加标题
    story.append(Paragraph('AI 企业解决方案对比分析报告', ModernHeading1))
    story.append(Spacer(1, 20))
    
    # 解析 Markdown 内容
    lines = md_content.split('\n')
    for line in lines:
        line = line.rstrip()
        if not line:
            story.append(Spacer(1, 10))
            continue
        
        if line.startswith('# '):
            story.append(Paragraph(line[2:], ModernHeading1))
            story.append(Spacer(1, 20))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], ModernHeading2))
            story.append(Spacer(1, 15))
        else:
            story.append(Paragraph(line, ModernStyle))
    
    # 生成 PDF
    doc.build(story)
    print(f'备用方案 PDF 生成成功: {pdf_path}')
