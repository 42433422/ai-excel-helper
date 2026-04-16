#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
XCAGI 商业计划书 Markdown 转 PDF
"""

import markdown2
from reportlab.lib import colors
from reportlab.lib import pagesizes
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
import os
import re

# 注册中文字体
try:
    pdfmetrics.registerFont(TTFont('SimSun', 'C:/Windows/Fonts/simsun.ttc'))
    pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
    pdfmetrics.registerFont(TTFont('MicrosoftYaHei', 'C:/Windows/Fonts/msyh.ttc'))
except:
    print("警告：未找到 Windows 字体，将使用默认字体")

def markdown_to_pdf(markdown_file, pdf_file):
    """将 Markdown 文件转换为 PDF"""
    
    # 读取 Markdown 文件
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
    
    # 转换为 HTML
    html = markdown2.markdown(markdown_text, extras=['tables', 'toc', 'fenced-code-blocks'])
    
    # 创建 PDF 文档
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # 存储 PDF 内容
    story = []
    
    # 定义样式
    styles = getSampleStyleSheet()
    
    # 自定义样式
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontName='SimHei',
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontName='SimHei',
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=12,
        spaceBefore=12
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontName='MicrosoftYaHei',
        fontSize=14,
        textColor=colors.darkgreen,
        spaceAfter=10,
        spaceBefore=10
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading3',
        parent=styles['Heading3'],
        fontName='MicrosoftYaHei',
        fontSize=12,
        textColor=colors.darkgreen,
        spaceAfter=8,
        spaceBefore=8
    ))
    
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontName='MicrosoftYaHei',
        fontSize=10,
        leading=14,
        spaceAfter=6,
        alignment=TA_LEFT
    ))
    
    # 解析 HTML 并添加内容
    lines = markdown_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            story.append(Spacer(1, 0.1*inch))
            continue
        
        # 处理标题
        if line.startswith('# '):
            title = line[2:].strip()
            story.append(Paragraph(title, styles['CustomTitle']))
            story.append(Spacer(1, 0.2*inch))
        elif line.startswith('## '):
            heading = line[3:].strip()
            story.append(Paragraph(heading, styles['CustomHeading1']))
            story.append(Spacer(1, 0.1*inch))
        elif line.startswith('### '):
            subheading = line[4:].strip()
            story.append(Paragraph(subheading, styles['CustomHeading2']))
            story.append(Spacer(1, 0.05*inch))
        elif line.startswith('#### '):
            subsubheading = line[5:].strip()
            story.append(Paragraph(subsubheading, styles['CustomHeading3']))
            story.append(Spacer(1, 0.05*inch))
        elif line.startswith('- ') or line.startswith('* '):
            # 列表项
            item = line[2:].strip()
            # 移除 markdown 格式
            item = re.sub(r'\*\*(.*?)\*\*', r'\1', item)
            item = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', item)
            story.append(Paragraph(f"• {item}", styles['CustomBody']))
        elif line.startswith('> '):
            # 引用
            quote = line[2:].strip()
            quote_style = ParagraphStyle(
                name='CustomQuote',
                parent=styles['Normal'],
                fontName='MicrosoftYaHei',
                fontSize=10,
                leading=14,
                leftIndent=20,
                borderColor=colors.grey,
                borderWidth=1,
                spaceAfter=6
            )
            story.append(Paragraph(quote, quote_style))
        elif line.startswith('|') and not line.startswith('|---'):
            # 表格行（简化处理）
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            # 移除 markdown 格式
            cells = [re.sub(r'\*\*(.*?)\*\*', r'\1', cell) for cell in cells]
            cells = [re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cell) for cell in cells]
            
            if len(cells) > 1:
                table = Table([cells], colWidths=[doc.width/len(cells)]*len(cells))
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'MicrosoftYaHei'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                story.append(table)
                story.append(Spacer(1, 0.05*inch))
        elif line.startswith('```'):
            # 代码块（跳过）
            continue
        elif not line.startswith('#') and not line.startswith('-') and not line.startswith('|'):
            # 普通段落
            # 移除 markdown 格式
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
            clean_line = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_line)
            clean_line = re.sub(r'`([^`]+)`', r'\1', clean_line)
            
            if clean_line.strip():
                story.append(Paragraph(clean_line, styles['CustomBody']))
                story.append(Spacer(1, 0.05*inch))
    
    # 添加分页符（可选）
    # story.append(PageBreak())
    
    # 构建 PDF
    doc.build(story)
    print(f"✓ PDF 生成成功：{pdf_file}")

if __name__ == '__main__':
    # 文件路径
    markdown_file = r'e:\FHD\.trae\documents\XCAGI 产品介绍（简洁版）.md'
    pdf_file = r'e:\FHD\.trae\documents\XCAGI 产品介绍（简洁版）.pdf'
    
    # 检查文件是否存在
    if not os.path.exists(markdown_file):
        print(f"错误：找不到 Markdown 文件 {markdown_file}")
    else:
        markdown_to_pdf(markdown_file, pdf_file)
