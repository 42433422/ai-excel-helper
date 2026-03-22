# -*- coding: utf-8 -*-
"""
TestShoeLabelGenerator - 标签模板生成器

此代码由 label-template-generator 自动生成，基于图片：oxxf5tzl74p48secr1eq.png
生成时间：2026-03-21 23:19:30
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TestShoeLabelGenerator:
    """标签模板生成器类"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.width = 502
        self.height = 621
        self.bg_color = "#000000"
        self.border_color = "#000000"
        self.text_color = "#000000"
        self.output_dir = output_dir or os.getcwd()
        
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取中文字体"""
        import platform
        
        font_paths = []
        
        if platform.system() == "Windows":
            font_paths = [
                "C:\\Windows\\Fonts\\simhei.ttf",
                "C:\\Windows\\Fonts\\msyh.ttc",
                "C:\\Windows\\Fonts\\simsun.ttc",
            ]
        elif platform.system() == "Darwin":
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ]
        else:
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        return ImageFont.load_default()
    
    def generate_label(self, product_data: Dict[str, Any], order_number: str, label_index: int = 1) -> Optional[str]:
        """
        生成标签图片
        
        Args:
            product_data: 产品数据字典
            order_number: 订单号
            label_index: 标签序号
            
        Returns:
            生成的文件名，失败返回 None
        """
        try:
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)
            
            self._draw_border(draw)
            self._draw_content(draw, product_data, order_number)
            
            os.makedirs(self.output_dir, exist_ok=True)
            safe_name = str(product_data.get('name', '') or product_data.get('product_name', ''))
            safe_name = safe_name.replace("/", "_").replace(" ", "_")[:20]
            filename = f"{order_number}_第{label_index}项_{safe_name}.png"
            output_path = os.path.join(self.output_dir, filename)
            image.save(output_path)
            logger.info(f"标签已生成：{output_path}")
            return filename
            
        except Exception as e:
            logger.error(f"生成标签失败：{e}")
            return None
    
    def _draw_border(self, draw: ImageDraw.ImageDraw):
        """绘制边框"""
        draw.rectangle([0, 0, self.width - 1, self.height - 1], outline=self.border_color, width=3)
    
    def _draw_content(self, draw: ImageDraw.ImageDraw, product_data: Dict[str, Any], order_number: str):
        """绘制标签内容 - 根据实际图片布局修改此方法"""
        
        y_offset = 40
        line_height = 50
        
        label_font = self._get_font(36)
        value_font = self._get_font(40)
        
        # 通用标签内容绘制
        draw.text((40, y_offset), "品名：", font=label_font, fill=self.text_color)
        draw.text((180, y_offset), str(product_data.get('product_name', '')), font=value_font, fill=self.text_color)
        y_offset += line_height
        
        draw.text((40, y_offset), "货号：", font=label_font, fill=self.text_color)
        draw.text((180, y_offset), str(product_data.get('item_number', '')), font=value_font, fill=self.text_color)
        y_offset += line_height
        
        draw.text((40, y_offset), "等级：", font=label_font, fill=self.text_color)
        draw.text((180, y_offset), str(product_data.get('grade', '合格品')), font=value_font, fill=self.text_color)
    
    def generate_labels_for_order(self, order_number: str, products: list) -> list:
        """
        为订单生成多个标签
        
        Args:
            order_number: 订单号
            products: 产品列表
            
        Returns:
            生成的文件名列表
        """
        labels = []
        for i, product in enumerate(products, 1):
            filename = self.generate_label(product, order_number, i)
            if filename:
                labels.append({
                    "filename": filename,
                    "order_number": order_number,
                    "label_index": i
                })
        return labels


def example_usage():
    """使用示例"""
    generator = TestShoeLabelGenerator(output_dir="./labels")
    
    product = {
        "product_name": "示例产品",
        "item_number": "12345",
        "grade": "合格品"
    }
    
    filename = generator.generate_label(product, "ORDER-001", 1)
    print(f"生成的标签：{filename}")


if __name__ == "__main__":
    example_usage()
