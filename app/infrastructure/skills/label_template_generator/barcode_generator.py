# -*- coding: utf-8 -*-
"""
Barcode Generator - 条形码生成器

支持多种条形码格式：EAN-13, Code128, Code39, UPC-A, ITF 等
"""

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class BarcodeGenerator:
    """条形码生成器类"""
    
    SUPPORTED_TYPES = ['ean13', 'ean8', 'code128', 'code39', 'upca', 'itf']
    
    def __init__(self, barcode_type: str = 'code128'):
        """
        初始化条形码生成器
        
        Args:
            barcode_type: 条形码类型，默认 code128
        """
        if barcode_type.lower() not in self.SUPPORTED_TYPES:
            logger.warning(f"不支持的条码类型：{barcode_type}，使用默认的 code128")
            barcode_type = 'code128'
        
        self.barcode_type = barcode_type.lower()
    
    def generate(self, data: str, options: Optional[Dict] = None) -> Optional[Image.Image]:
        """
        生成条形码图像
        
        Args:
            data: 条码数据字符串
            options: 可选配置项
                    - writer: 'png', 'svg' (默认 png)
                    - width: 条码宽度倍数 (默认 2)
                    - height: 条码高度 (默认 50)
                    - show_text: 是否显示下方文本 (默认 True)
                    - text_distance: 文本与条码距离 (默认 5)
                    - font_size: 文本字体大小 (默认 10)
                    - foreground: 前景色 (默认黑色)
                    - background: 背景色 (默认白色)
        
        Returns:
            PIL Image 对象，失败返回 None
        """
        try:
            from barcode import get_barcode
            from barcode.writer import ImageWriter
            
            options = options or {}
            
            # 配置写入器选项
            writer_options = {
                'module_width': float(options.get('width', 2)),
                'module_height': float(options.get('height', 50)),
                'quiet_zone': float(options.get('quiet_zone', 6.5)),
                'font_size': int(options.get('font_size', 10)),
                'text_distance': float(options.get('text_distance', 5)),
                'show_text': options.get('show_text', True),
                'foreground': options.get('foreground', '000000'),
                'background': options.get('background', 'ffffff'),
                'compress': options.get('compress', False),
            }
            
            # 创建条码写入器
            writer = ImageWriter()
            
            # 获取条码类
            barcode_class = get_barcode(self.barcode_type)
            
            # 生成条码
            # 注意：barcode 库需要数据符合特定格式
            # EAN-13 需要 12 或 13 位数字，会自动计算校验位
            cleaned_data = self._clean_barcode_data(data, self.barcode_type)
            
            if not cleaned_data:
                logger.error(f"条码数据格式不正确：{data}")
                return None
            
            # 生成条码图像
            barcode = barcode_class(cleaned_data, writer=writer)
            
            # 保存到 BytesIO
            buffer = io.BytesIO()
            barcode.write(buffer, options=writer_options)
            buffer.seek(0)
            
            # 转换为 PIL Image
            img = Image.open(buffer)
            
            return img
            
        except ImportError:
            logger.error("需要安装 python-barcode 库：pip install python-barcode")
            return self._generate_fallback_barcode(data, options)
        except Exception as e:
            logger.error(f"生成条码失败：{e}")
            return self._generate_fallback_barcode(data, options)
    
    def _clean_barcode_data(self, data: str, barcode_type: str) -> str:
        """
        清理和验证条码数据
        
        Args:
            data: 原始数据
            barcode_type: 条码类型
            
        Returns:
            清理后的数据，如果无效返回空字符串
        """
        if not data:
            return ''
        
        # 转换为字符串
        data = str(data).strip()
        
        # 移除空格和特殊字符（保留数字和字母）
        if barcode_type in ['ean13', 'ean8', 'upca', 'itf']:
            # 数字型条码只保留数字
            cleaned = ''.join(c for c in data if c.isdigit())
        else:
            # Code128 和 Code39 支持字母数字
            cleaned = ''.join(c for c in data if c.isalnum())
        
        # 根据条码类型调整长度
        if barcode_type == 'ean13':
            if len(cleaned) < 12:
                cleaned = cleaned.ljust(12, '0')
            elif len(cleaned) > 13:
                cleaned = cleaned[:13]
        elif barcode_type == 'ean8':
            if len(cleaned) < 7:
                cleaned = cleaned.ljust(7, '0')
            elif len(cleaned) > 8:
                cleaned = cleaned[:8]
        elif barcode_type == 'upca':
            if len(cleaned) < 11:
                cleaned = cleaned.ljust(11, '0')
            elif len(cleaned) > 12:
                cleaned = cleaned[:12]
        
        return cleaned
    
    def _generate_fallback_barcode(self, data: str, options: Optional[Dict] = None) -> Image.Image:
        """
        回退方案：生成简单的条码占位图（当 python-barcode 未安装时）
        """
        width = 400
        height = int(options.get('height', 50)) if options else 50
        
        img = Image.new('RGB', (width, height + 20), 'white')
        draw = ImageDraw.Draw(img)
        
        # 绘制简单的黑白条纹
        import random
        random.seed(hash(data))  # 相同数据生成相同条码
        
        x = 10
        bar_width = 2
        for _ in range(80):
            bar_height = random.randint(height // 2, height)
            draw.rectangle(
                [x, 0, x + bar_width, bar_height],
                fill='black'
            )
            x += bar_width + random.randint(1, 3)
        
        # 绘制下方文本
        if options and options.get('show_text', True):
            draw.text((10, height + 5), str(data)[:30], fill='black')
        
        return img
    
    def save(self, filename: str, data: str, options: Optional[Dict] = None) -> bool:
        """
        保存条形码为图片文件
        
        Args:
            filename: 输出文件路径
            data: 条码数据
            options: 配置选项
            
        Returns:
            是否成功
        """
        try:
            img = self.generate(data, options)
            if img:
                img.save(filename)
                logger.info(f"条码已保存：{filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"保存条码失败：{e}")
            return False
    
    @staticmethod
    def get_supported_types() -> List[str]:
        """获取支持的条码类型列表"""
        return BarcodeGenerator.SUPPORTED_TYPES.copy()
    
    @staticmethod
    def get_type_description(barcode_type: str) -> str:
        """获取条码类型的描述信息"""
        descriptions = {
            'ean13': 'EAN-13: 国际商品条码（13 位数字）',
            'ean8': 'EAN-8: 缩短版商品条码（8 位数字）',
            'code128': 'Code 128: 高密度条码（字母数字）',
            'code39': 'Code 39: 工业标准条码（字母数字）',
            'upca': 'UPC-A: 北美商品条码（12 位数字）',
            'itf': 'ITF: 交叉 25 码（数字，用于包装）'
        }
        return descriptions.get(barcode_type.lower(), f'{barcode_type}: 未知类型')


# 导入 ImageDraw 用于回退方案
try:
    from PIL import ImageDraw
except ImportError:
    ImageDraw = None


def generate_barcode(
    data: str,
    barcode_type: str = 'code128',
    options: Optional[Dict] = None
) -> Optional[Image.Image]:
    """
    便捷函数：生成条形码
    
    Args:
        data: 条码数据
        barcode_type: 条码类型
        options: 配置选项
        
    Returns:
        PIL Image 对象
    """
    generator = BarcodeGenerator(barcode_type)
    return generator.generate(data, options)


def save_barcode(
    filename: str,
    data: str,
    barcode_type: str = 'code128',
    options: Optional[Dict] = None
) -> bool:
    """
    便捷函数：保存条形码到文件
    
    Args:
        filename: 输出文件路径
        data: 条码数据
        barcode_type: 条码类型
        options: 配置选项
        
    Returns:
        是否成功
    """
    generator = BarcodeGenerator(barcode_type)
    return generator.save(filename, data, options)
