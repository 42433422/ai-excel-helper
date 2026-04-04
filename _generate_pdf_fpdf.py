from fpdf import FPDF

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('SimHei', '', 'C:\\Windows\\Fonts\\simhei.ttf', uni=True)
    
    def header(self):
        self.set_font('SimHei', '', 16)
        self.cell(0, 10, 'AI 企业解决方案对比分析报告', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('SimHei', '', 10)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')

md_path = r'e:\FHD\XCAGI\AI企业解决方案对比分析报告.md'
pdf_path = r'e:\FHD\XCAGI\AI企业解决方案对比分析报告.pdf'

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

pdf = PDF()
pdf.add_page()
pdf.set_font('SimHei', '', 12)

for line in lines:
    line = line.rstrip()
    if not line:
        pdf.ln(5)
        continue
    
    if line.startswith('# '):
        pdf.set_font('SimHei', '', 16)
        pdf.cell(0, 10, line[2:], 0, 1, 'L')
        pdf.ln(5)
        pdf.set_font('SimHei', '', 12)
    elif line.startswith('## '):
        pdf.set_font('SimHei', '', 14)
        pdf.cell(0, 10, line[3:], 0, 1, 'L')
        pdf.ln(3)
        pdf.set_font('SimHei', '', 12)
    elif line.startswith('### '):
        pdf.set_font('SimHei', '', 12)
        pdf.set_text_color(0, 0, 128)
        pdf.cell(0, 8, line[4:], 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
    elif line.startswith('|'):
        # 简单处理表格
        pdf.multi_cell(0, 8, line)
    elif line.startswith('```'):
        # 代码块
        pdf.set_font('Courier', '', 10)
        pdf.multi_cell(0, 6, line)
        pdf.set_font('SimHei', '', 12)
    else:
        pdf.multi_cell(0, 6, line)

pdf.output(pdf_path)
print(f'PDF generated successfully: {pdf_path}')
