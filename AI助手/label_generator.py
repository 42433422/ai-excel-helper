from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

class ProductLabelGenerator:
    def __init__(self):
        self.width = 900
        self.height = 600
        self.bg_color = (255, 255, 255)
        self.border_color = (0, 0, 0)
        self.text_color = (0, 0, 0)
        self.header_bg = (220, 240, 255)
        
        self.font_sizes = {
            'title': 36,      # 从32增加到36
            'value_large': 60, # 从54增加到60
            'value_medium': 46, # 从42增加到46
            'value_small': 36, # 从32增加到36
            'ratio_header': 32, # 从28增加到32
            'ratio_value': 34, # 从30增加到34
            'footer': 52      # 从48增加到52
        }
        
        self.columns = {
            'label': [0, 180],
            'col1': [180, 320],
            'col2': [500, 150],
            'col3': [650, 150]
        }
        
    def get_font(self, size):
        font_paths = [
            "msyhbd.ttf",  # 优先使用粗体字体
            "simhei.ttf",
            "simsun.ttc",
            "arial.ttf",
            "times.ttf",
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        import sys
        if sys.platform == 'win32':
            win_fonts = [
                "C:\\Windows\\Fonts\\msyhbd.ttf",  # 优先使用粗体字体
                "C:\\Windows\\Fonts\\simhei.ttf",
                "C:\\Windows\\Fonts\\simsun.ttc",
                "C:\\Windows\\Fonts\\msyh.ttf",
            ]
            for font_path in win_fonts:
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        
        return ImageFont.load_default()
    
    def generate_label(self, product_data, output_path):
        image = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(image)
        
        draw.rectangle([0, 0, self.width-1, self.height-1], outline=self.border_color, width=3)
        
        # 判断产品名称是否包含"剂"或"料"，决定是否显示参考配比
        product_name = product_data.get('product_name', '')
        has_ratio = not any(keyword in product_name for keyword in ['剂', '料'])
        
        label_x = 20
        label_width = 180
        col1_x = 180
        col1_width = 320
        col2_x = 500
        col2_width = 150
        col3_x = 650
        
        y_pn = 25
        h_pn = 70
        y_name = y_pn + h_pn + 20  # 增加20px间距
        h_name = 62
        
        # 根据是否有参考配比调整布局
        if has_ratio:
            # 有参考配比的布局
            y_ratio = y_name + h_name + 20
            h_ratio = 94  # 参考配比区域更高，包含两行
            y_date = y_ratio + h_ratio + 20  # 增加20px间距
            h_date = 62
            y_spec = y_date + h_date + 20  # 增加20px间距
            h_spec = 62
            y_footer = y_spec + h_spec + 20  # 增加20px间距
        else:
            # 无参考配比的布局，保持原来的4个区域，但5个区域均匀分布
            # 保持原来的两列布局：生产日期+保质期、规格+检验员
            # 5个区域：产品编号、产品名称、生产日期+保质期、规格+检验员、底部空白
            
            # 产品编号区域：25-125px (100px)
            y_pn = 25
            h_pn = 100
            
            # 产品名称区域：125-225px (100px)
            y_name = y_pn + h_pn
            h_name = 100
            
            # 生产日期+保质期区域：225-325px (100px)
            y_date = y_name + h_name
            h_date = 100
            
            # 规格+检验员区域：325-425px (100px)
            y_spec = y_date + h_date
            h_spec = 100
            
            # 底部空白：425-600px (175px)
        
        # 添加垂直分割线
        if has_ratio:
            draw.line([label_x + label_width, y_pn, label_x + label_width, y_spec + h_spec], fill=self.border_color, width=2)  # 左边分割线
            draw.line([col2_x + col2_width, y_date, col2_x + col2_width, y_spec + h_spec], fill=self.border_color, width=2)  # 右边分割线（生产日期和产品规格）
            draw.line([col1_x + col1_width, y_date, col1_x + col1_width, y_spec + h_spec], fill=self.border_color, width=2)  # 中间分割线（延伸到产品规格）
        else:
            # 无参考配比的分割线 - 保持原来的两列布局
            draw.line([label_x + label_width, y_pn, label_x + label_width, 599], fill=self.border_color, width=2)  # 左边分割线延伸到标签底部
            draw.line([col2_x + col2_width, y_date, col2_x + col2_width, 599], fill=self.border_color, width=2)  # 右边分割线延伸到标签底部
        
        # 水平分隔线
        draw.line([20, y_pn + h_pn, 880, y_pn + h_pn], fill=self.border_color, width=2)
        draw.line([20, y_name + h_name, 880, y_name + h_name], fill=self.border_color, width=2)
        
        if has_ratio:
            draw.line([20, y_ratio + h_ratio, 880, y_ratio + h_ratio], fill=self.border_color, width=2)  # 参考配比结束线
        
        draw.line([20, y_date + h_date, 880, y_date + h_date], fill=self.border_color, width=2)
        draw.line([20, y_spec + h_spec, 880, y_spec + h_spec], fill=self.border_color, width=2)
        
        # 移除产品编号的蓝色背景
        
        # 产品编号 - 居中显示
        # 产品编号 - 增大字体，恢复原来的居中逻辑
        pn_label_font = self.get_font(40)  # 增大字体从32到40
        pn_value_font = self.get_font(70)  # 增大字体从66到70
        
        draw.text((45, y_pn + 12), "产品编号", font=pn_label_font, fill=self.text_color)  # 标签位置不变
        
        pn_value = product_data.get('product_number', '')
        # 恢复原来的居中逻辑 - 在680px宽的数值区域居中
        pn_value_bbox = draw.textbbox((0, 0), pn_value, font=pn_value_font)
        pn_value_width = pn_value_bbox[2] - pn_value_bbox[0]
        pn_value_x = 200 + (680 - pn_value_width) // 2  # 在680px宽的数值区域居中
        draw.text((pn_value_x, y_pn + 12), pn_value, font=pn_value_font, fill=self.text_color)
        
        # 产品名称 - 增大字体，恢复原来的居中逻辑
        name_label_font = self.get_font(40)  # 增大字体从32到40
        name_value_font = self.get_font(58)  # 增大字体从54到58
        
        draw.text((45, y_name + 12), "产品名称", font=name_label_font, fill=self.text_color)  # 标签位置不变
        
        name_value = product_data.get('product_name', '')
        # 恢复原来的居中逻辑 - 在680px宽的数值区域居中
        name_value_bbox = draw.textbbox((0, 0), name_value, font=name_value_font)
        name_value_width = name_value_bbox[2] - name_value_bbox[0]
        name_value_x = 200 + (680 - name_value_width) // 2  # 在680px宽的数值区域居中
        draw.text((name_value_x, y_name + 12), name_value, font=name_value_font, fill=self.text_color)
        
        # 参考配比区域 - 动态适应不同配比
        if has_ratio:
            draw.text((45, y_ratio + 10), "参考配比", font=self.get_font(32), fill=self.text_color)
            
            # 获取参考配比数据
            ratio_text = product_data.get('ratio', '1 : 0.5-0.6 : 0.5-0.8')
            
            # 解析配比数据格式："主剂：兰水：稀释剂：白水，100 : 1.2-1.5 : 50-70 : 1.5-1.8"
            # 或者："主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7"
            try:
                if '，' in ratio_text:
                    # 格式：表头，数值
                    parts = ratio_text.split('，', 1)
                    headers_text = parts[0].strip()
                    values_text = parts[1].strip()
                    
                    # 解析表头 - 使用中文分号
                    headers = [h.strip() for h in headers_text.split('：')]
                    
                    # 解析数值 - 处理中文和英文冒号的混合
                    # 先替换中文冒号为英文冒号，然后分割
                    values_text_normalized = values_text.replace('：', ':').replace(' ', '')
                    values = [v.strip() for v in values_text_normalized.split(':')]
                else:
                    # 格式：主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7
                    # 默认表头
                    headers = ["主剂", "固化剂", "稀释剂"]
                    values = ["1", "0.7-0.8", "0.5-0.7"]
                
                # 动态计算列数
                num_columns = len(headers)
                if len(values) != num_columns:
                    values = values[:num_columns] + ['0'] * (num_columns - len(values))
                
            except Exception as e:
                # 解析失败时的默认值
                headers = ["主剂", "固化剂", "稀释剂"]
                values = ["1", "0.7-0.8", "0.5-0.7"]
            
            # 使用整个内容区域宽度（700像素：从180到880）
            content_width = 880 - 180  # 700像素
            ratio_col_width = content_width // num_columns  # 动态列宽
            
            # 绘制表头
            header_font = self.get_font(28)
            for i, header in enumerate(headers):
                bbox = draw.textbbox((0, 0), header, font=header_font)
                text_width = bbox[2] - bbox[0]
                col_start_x = col1_x + i * ratio_col_width
                text_x = col_start_x + (ratio_col_width - text_width) // 2
                draw.text((text_x, y_ratio + 10), header, font=header_font, fill=self.text_color)
            
            # 绘制配比数值
            ratio_font = self.get_font(30)
            for i, value in enumerate(values):
                bbox = draw.textbbox((0, 0), str(value), font=ratio_font)
                part_width = bbox[2] - bbox[0]
                col_start_x = col1_x + i * ratio_col_width
                text_x = col_start_x + (ratio_col_width - part_width) // 2
                draw.text((text_x, y_ratio + 45), str(value), font=ratio_font, fill=self.text_color)
        
        # 生产日期和保质期区域 - 增大字体，保持原来的位置
        date_font = self.get_font(38)  # 增大字体
        
        draw.text((45, y_date + 12), "生产日期", font=date_font, fill=self.text_color)
        draw.text((210, y_date + 12), product_data.get('production_date', ''), font=date_font, fill=self.text_color)
        draw.text((520, y_date + 12), "保质期", font=date_font, fill=self.text_color)
        draw.text((670, y_date + 12), product_data.get('shelf_life', ''), font=date_font, fill=self.text_color)
        
        draw.text((45, y_spec + 12), "产品规格", font=date_font, fill=self.text_color)
        draw.text((210, y_spec + 12), product_data.get('specification', ''), font=date_font, fill=self.text_color)
        draw.text((520, y_spec + 12), "检验员", font=date_font, fill=self.text_color)
        draw.text((670, y_spec + 12), product_data.get('inspector', ''), font=date_font, fill=self.text_color)
        
        # 底部提示文字 - 在最后一格中居中
        if has_ratio:
            footer_text = "请充分搅拌均匀后使用"
            footer_font = self.get_font(48)
            bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # 计算在最后一格中居中的位置
            footer_area_start_x = 20
            footer_area_end_x = 880
            footer_area_width = footer_area_end_x - footer_area_start_x
            footer_x = footer_area_start_x + (footer_area_width - text_width) // 2
            # 垂直居中
            footer_y = y_footer + (h_spec - text_height) // 2
            draw.text((footer_x, footer_y), footer_text, font=footer_font, fill=self.text_color)
        
        image.save(output_path)
        
        # 自动转换为PDF
        pdf_output_path = self.convert_to_pdf(output_path)
        return pdf_output_path
    
    def convert_to_pdf(self, image_path):
        """
        将PNG标签转换为PDF格式
        
        Args:
            image_path: PNG图像路径
            
        Returns:
            str: PDF文件路径
        """
        try:
            # 获取原始文件名（不含路径和扩展名）
            original_filename = os.path.splitext(os.path.basename(image_path))[0]
            
            # PDF输出到"PDF文件"目录
            pdf_output_dir = "PDF文件"
            if not os.path.exists(pdf_output_dir):
                os.makedirs(pdf_output_dir)
            
            # 生成PDF输出路径
            pdf_output_path = os.path.join(pdf_output_dir, f"{original_filename}.pdf")
            
            # 创建PDF
            c = canvas.Canvas(pdf_output_path, pagesize=landscape(A4))
            
            # 计算标签位置（居中）
            a4_width, a4_height = landscape(A4)
            
            # 打开图像获取尺寸
            with Image.open(image_path) as img:
                img_width, img_height = img.size
                
                # 计算缩放比例，确保图像适合页面
                scale = min(
                    (a4_width - 40*mm) / img_width,
                    (a4_height - 40*mm) / img_height
                )
                
                # 计算居中位置
                x = (a4_width - img_width * scale) / 2
                y = (a4_height - img_height * scale) / 2
                
                # 绘制图像
                c.drawImage(image_path, x, y, width=img_width*scale, height=img_height*scale)
            
            # 保存PDF
            c.save()
            
            # 保留PNG文件（保存在"商标导出"目录）
            # PNG文件已经保存在"商标导出"目录，不需要清理
            # PDF文件保存在"PDF文件"目录
            
            return pdf_output_path
            
        except Exception as e:
            # 如果转换失败，返回原始PNG路径
            return image_path
    
    def cleanup_old_pdfs(self, directory):
        """
        清理目录中的旧PDF文件
        
        Args:
            directory: 要清理的目录路径
        """
        try:
            if not os.path.exists(directory):
                return
            
            # 遍历目录中的文件
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                # 只处理PDF文件
                if os.path.isfile(file_path) and filename.endswith('.pdf'):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        pass
        except Exception as e:
            pass

def generate_sample_label():
    generator = ProductLabelGenerator()
    sample_data = {
        'product_number': '7225-70F',
        'product_name': 'PU净味三分光清面漆',
        'ratio': '1 : 0.5-0.6 : 0.5-0.8',
        'production_date': '2025.12.25',
        'shelf_life': '6个月',
        'specification': '20±0.1KG',
        'inspector': '合格 (01)'
    }
    
    output_path = os.path.join(os.path.dirname(__file__), 'outputs', 'sample_label.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    return generator.generate_label(sample_data, output_path)

if __name__ == "__main__":
    result = generate_sample_label()
    print(f"示例标签已生成: {result}")
