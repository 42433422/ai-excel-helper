# -*- coding: utf-8 -*-
"""
TestPEWhiteBottomPaint - 标签模板生成器

此代码由 label-template-generator 自动生成，基于图片: 26-0300001A_第1项_PE白底漆.png
生成时间: 2026-03-23 00:39:09

固定标签和可变数据字段已自动识别。
保留原始精确位置信息。
"""

import os
import platform
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TestPEWhiteBottomPaint:
    """标签模板生成器类 - 支持动态数据填充"""

    def __init__(self, output_dir: Optional[str] = None):
        self.width = 900
        self.height = 600
        self.bg_color = "#ffffff"
        self.border_color = "#000000"
        self.text_color = "#000000"
        self.output_dir = output_dir or os.getcwd()

        # 定义固定标签和对应的字段（包含位置信息）
        self.fields = {
            "product_number": {
                "label": "产品编号",
                "default_value": "",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 27, "y": 20, "width": 175, "height": 60}
            },
            "9803": {
                "label": "9803",
                "default_value": "",
                "type": "dynamic",
                "editable": False,
                "position": {"x": 461, "y": 32, "width": 161, "height": 69}
            },
            "product_name": {
                "label": "产品名称",
                "default_value": "",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 27, "y": 114, "width": 175, "height": 56}
            },
            "PE白底漆": {
                "label": "PE白底漆",
                "default_value": "",
                "type": "dynamic",
                "editable": False,
                "position": {"x": 414, "y": 116, "width": 251, "height": 70}
            },
            "参考配比": {
                "label": "参考配比",
                "default_value": "",
                "type": "dynamic",
                "editable": False,
                "position": {"x": 26, "y": 197, "width": 145, "height": 49}
            },
            "1 : 0.5-0.6 : 0.5-0.8": {
                "label": "1 : 0.5-0.6 : 0.5-0.8",
                "default_value": "",
                "type": "dynamic",
                "editable": False,
                "position": {"x": 330, "y": 202, "width": 420, "height": 43}
            },
            "production_date": {
                "label": "生产日期",
                "default_value": "2026.03.22",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 29, "y": 319, "width": 170, "height": 48}
            },
            "shelf_life": {
                "label": "保质期",
                "default_value": "6个月",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 514, "y": 315, "width": 132, "height": 55}
            },
            "product_spec": {
                "label": "产品规格",
                "default_value": "2.0±0.1KG/桶",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 31, "y": 404, "width": 167, "height": 45}
            },
            "inspector": {
                "label": "检验员",
                "default_value": "合格",
                "type": "fixed_label",
                "editable": True,
                "position": {"x": 518, "y": 403, "width": 127, "height": 48}
            },
            "请充分搅拌均匀后使用": {
                "label": "请充分搅拌均匀后使用",
                "default_value": "",
                "type": "dynamic",
                "editable": False,
                "position": {"x": 203, "y": 480, "width": 492, "height": 61}
            },
        }

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取中文字体"""

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

    def generate_label(
        self,
        data: Dict[str, Any],
        order_number: str = "",
        label_index: int = 1
    ) -> Optional[str]:
        """
        生成标签图片

        Args:
            data: 数据字典，包含所有字段值
            order_number: 订单号（可选）
            label_index: 标签序号

        Returns:
            生成的文件名，失败返回 None
        """
        try:
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)

            self._draw_border(draw)
            self._draw_grid(draw)
            self._draw_fields(draw, data)

            os.makedirs(self.output_dir, exist_ok=True)

            # 生成文件名
            product_name = data.get('product_name', data.get('item_number', 'label'))
            safe_name = str(product_name).replace("/", "_").replace(" ", "_")[:20]

            if order_number:
                filename = f"{order_number}_第{label_index}项_{safe_name}.png"
            else:
                filename = f"label_{safe_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"

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

    def _draw_grid(self, draw: ImageDraw.ImageDraw):
        """绘制内部网格线"""
        draw.line([(200, 0), (200, self.height)], fill=self.border_color, width=1)
        draw.line([(500, 0), (500, self.height)], fill=self.border_color, width=1)

    def _draw_fields(self, draw: ImageDraw.ImageDraw, data: Dict[str, Any]):
        """绘制所有字段 - 使用精确位置"""
        for field_key, field_info in self.fields.items():
            pos = field_info.get('position', {})
            x = pos.get('x', 40)
            y = pos.get('y', 40)
            width = pos.get('width', 0)
            height = pos.get('height', 0)

            # 根据位置自适应字体大小
            if height > 0:
                font_size = min(int(height * 0.7), 40)
            else:
                font_size = 32

            label = field_info['label']
            value = data.get(field_key, field_info.get('default_value', ''))
            is_merged = field_info.get('is_merged', False)

            if is_merged and value:
                # 合并单元格：标签和值分开显示
                draw.text((x, y), label, font=self._get_font(font_size), fill=self.text_color)
                value_x = x + width + 10
                draw.text((value_x, y), str(value), font=self._get_font(font_size), fill=self.text_color)
            elif value:
                # 有值但非合并：标签和值分开显示
                draw.text((x, y), label, font=self._get_font(font_size), fill=self.text_color)
                value_x = x + width + 10
                draw.text((value_x, y), str(value), font=self._get_font(font_size), fill=self.text_color)
            else:
                # 只有标签，没有值
                draw.text((x, y), label, font=self._get_font(font_size), fill=self.text_color)

    def get_field_template(self) -> Dict[str, Any]:
        """获取字段模板"""
        return {{
            field_key: {{
                "label": info["label"],
                "type": info["type"],
                "editable": info["editable"],
                "example_value": info.get("default_value", ""),
                "position": info.get("position", {{}})
            }}
            for field_key, info in self.fields.items()
        }}


def example_usage():
    """使用示例"""
    generator = TestPEWhiteBottomPaint(output_dir="./labels")

    data = {
        "product_name": "PE白底漆",
        "product_no": "9803",
    }

    filename = generator.generate_label(data, "ORDER-001", 1)
    print(f"生成的标签：{filename}")


if __name__ == "__main__":
    example_usage()
