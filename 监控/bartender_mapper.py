#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BarTender 标签信息映射程序
功能：
1. 识别 BarTender 窗口
2. 检测窗口中的白色标签区域
3. 使用 OCR 提取文字
4. 表格化映射输出
"""

import sys
import os
import argparse
import logging
import numpy as np
import cv2
from PIL import Image, ImageGrab
import win32gui
import win32con
import win32api
from typing import Dict, List, Optional, Tuple

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("警告: easyocr 未安装，将使用模拟数据")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bartender_mapping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BarTenderWindowRecognizer:
    """BarTender 窗口识别器"""
    
    def __init__(self):
        self.bartend_class = "BarTender10x"  # BarTender 窗口类名
        self.bartend_title = "BarTender"
    
    def find_bartender_windows(self) -> List[Dict]:
        """查找所有 BarTender 窗口"""
        windows = []
        
        def enum_callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                
                # 检查是否是 BarTender 窗口
                if 'bartend' in class_name.lower() or 'BarTender' in title:
                    rect = win32gui.GetWindowRect(hwnd)
                    window_info = {
                        'hwnd': hwnd,
                        'title': title,
                        'class': class_name,
                        'left': rect[0],
                        'top': rect[1],
                        'right': rect[2],
                        'bottom': rect[3],
                        'width': rect[2] - rect[0],
                        'height': rect[3] - rect[1]
                    }
                    windows_list.append(window_info)
            
            return True
        
        win32gui.EnumWindows(enum_callback, windows)
        logger.info(f"找到 {len(windows)} 个 BarTender 窗口")
        return windows
    
    def capture_window(self, hwnd: int) -> Image.Image:
        """截取窗口内容"""
        try:
            # 获取窗口客户区大小
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            
            # 获取窗口位置
            rect = win32gui.GetWindowRect(hwnd)
            
            # 使用 ImageGrab 截取窗口
            img = ImageGrab.grab(rect)
            logger.info(f"成功截取窗口，尺寸: {img.size}")
            return img
            
        except Exception as e:
            logger.error(f"截取窗口失败: {str(e)}")
            raise Exception(f"截取窗口失败: {str(e)}")


class WhiteRegionDetector:
    """白色区域检测器"""
    
    def __init__(self, white_threshold: int = 220):
        """
        初始化白色区域检测器
        white_threshold: 白色阈值 (0-255)，高于此值视为白色
        """
        self.white_threshold = white_threshold
    
    def detect_white_regions(self, image: Image.Image, is_full_window: bool = False) -> List[Tuple[int, int, int, int]]:
        """
        检测图像中的白色区域
        is_full_window: 是否是整个窗口（需要排除边缘区域）
        返回: 白色区域的边界框列表 [(x1, y1, x2, y2), ...]
        """
        # 转换为 numpy 数组
        img_array = np.array(image)
        
        # 转换为灰度图
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # 高斯模糊以减少噪声
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 二值化 - 使用更高阈值只保留纯白色区域
        _, binary = cv2.threshold(blurred, self.white_threshold, 255, cv2.THRESH_BINARY)
        
        # 形态学操作
        kernel = np.ones((5, 5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 筛选白色区域（标签区域）
        white_regions = []
        image_width = image.width
        image_height = image.height
        
        # 计算排除区域（边缘、菜单栏等）
        margin = 5  # 边缘留白
        if is_full_window:
            # 排除顶部菜单栏区域（通常在顶部50像素内）
            top_exclude = 60
            # 排除左右边缘
            left_exclude = 10
            right_exclude = 10
        else:
            top_exclude = margin
            left_exclude = margin
            right_exclude = margin
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # 计算宽高比
            aspect_ratio = w / h if h > 0 else 0
            
            # 标签区域特征：
            # 1. 面积足够大（>10000像素）
            # 2. 宽高比合理（标签通常是横向的，0.5 < ratio < 5）
            # 3. 不在边缘排除区域
            # 4. 宽度占图像宽度的较大比例（>30%）
            
            width_ratio = w / image_width if image_width > 0 else 0
            
            is_valid_label = (
                area > 10000 and  # 面积足够大
                0.3 < aspect_ratio < 4 and  # 宽高比合理
                w > image_width * 0.3 and  # 宽度占图像30%以上
                x > left_exclude and  # 不在左侧边缘
                x + w < image_width - right_exclude and  # 不在右侧边缘
                y > top_exclude  # 不在顶部边缘
            )
            
            if is_valid_label:
                # 扩大一点区域边界
                x1 = max(0, x - 5)
                y1 = max(0, y - 5)
                x2 = min(image_width, x + w + 5)
                y2 = min(image_height, y + h + 5)
                white_regions.append((x1, y1, x2, y2))
        
        # 合并重叠区域
        if white_regions:
            white_regions = self._merge_overlapping_regions(white_regions)
        
        logger.info(f"检测到 {len(white_regions)} 个白色标签区域")
        return white_regions
    
    def _merge_overlapping_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """合并重叠的区域"""
        if not regions:
            return regions
        
        # 按面积排序（从大到小）
        regions = sorted(regions, key=lambda r: (r[2]-r[0])*(r[3]-r[1]), reverse=True)
        merged = []
        
        for region in regions:
            x1, y1, x2, y2 = region
            is_overlapping = False
            
            for i, existing in enumerate(merged):
                ex1, ey1, ex2, ey2 = existing
                # 检查是否重叠（重叠超过50%）
                overlap_x1 = max(x1, ex1)
                overlap_y1 = max(y1, ey1)
                overlap_x2 = min(x2, ex2)
                overlap_y2 = min(y2, ey2)
                
                if overlap_x1 < overlap_x2 and overlap_y1 < overlap_y2:
                    overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                    region_area = (x2 - x1) * (y2 - y1)
                    
                    if overlap_area > region_area * 0.3:
                        # 合并区域
                        merged[i] = (min(x1, ex1), min(y1, ey1), max(x2, ex2), max(y2, ey2))
                        is_overlapping = True
                        break
            
            if not is_overlapping:
                merged.append(region)
        
        return merged
    
    def crop_white_regions(self, image: Image.Image, regions: List[Tuple[int, int, int, int]]) -> List[Image.Image]:
        """裁剪白色区域"""
        cropped_images = []
        for i, (x1, y1, x2, y2) in enumerate(regions):
            # 扩大一点区域边界
            x1 = max(0, x1 - 5)
            y1 = max(0, y1 - 5)
            x2 = min(image.width, x2 + 5)
            y2 = min(image.height, y2 + 5)
            
            cropped = image.crop((x1, y1, x2, y2))
            cropped_images.append(cropped)
            logger.info(f"裁剪白色区域 {i+1}: 尺寸 {cropped.size}")
        
        return cropped_images
    
    def save_debug_image(self, image: Image.Image, regions: List[Tuple[int, int, int, int]], output_path: str):
        """保存调试图像，标记检测到的白色区域"""
        img_array = np.array(image).copy()
        
        for i, (x1, y1, x2, y2) in enumerate(regions):
            # 绘制矩形框（绿色）
            color = (0, 255, 0)
            cv2.rectangle(img_array, (x1, y1), (x2, y2), color, 3)
            # 添加编号
            cv2.putText(img_array, f"Label {i+1}", (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # 保存图像
        debug_img = Image.fromarray(img_array)
        debug_img.save(output_path)
        logger.info(f"调试图像已保存: {output_path}")


class BartenderInfoMapper:
    """BarTender 信息映射器"""
    
    def __init__(self):
        self.window_recognizer = BarTenderWindowRecognizer()
        self.white_detector = WhiteRegionDetector(white_threshold=200)
        self.ocr_reader = None
        
        if EASYOCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                logger.info("EasyOCR 初始化成功")
            except Exception as e:
                logger.error(f"EasyOCR 初始化失败: {str(e)}")
                self.ocr_reader = None
    
    def extract_text_from_image(self, image: Image.Image) -> List[Dict]:
        """从图像中提取文字及位置信息"""
        if self.ocr_reader is not None:
            try:
                img_array = np.array(image)
                results = self.ocr_reader.readtext(img_array)
                
                text_items = []
                for result in results:
                    bbox, text, confidence = result
                    if confidence > 0.4:
                        # 计算边界框的中心点和区域
                        x1, y1 = bbox[0]
                        x2, y2 = bbox[2]
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        width = x2 - x1
                        height = y2 - y1
                        
                        text_items.append({
                            'text': text,
                            'confidence': confidence,
                            'bbox': bbox,
                            'center_x': center_x,
                            'center_y': center_y,
                            'width': width,
                            'height': height,
                            'top': y1,
                            'bottom': y2,
                            'left': x1,
                            'right': x2
                        })
                
                logger.info(f"OCR 提取成功，识别到 {len(text_items)} 个文本项")
                return text_items
                
            except Exception as e:
                logger.error(f"OCR 提取失败: {str(e)}")
                return []
        else:
            return []
    
    def _get_mock_data(self) -> str:
        """获取模拟数据"""
        return """产品名称：6821A白底
型号规格：18L
生产厂家：佳诺涂料有限公司
生产日期：2026-01-26
保质期：12个月
执行标准：GB/T 1725-2007
净含量：18升
使用说明：请按照说明书正确使用
注意事项：存放于阴凉干燥处，远离火源"""
    
    def classify_regions_with_position(self, text_items: List[Dict], image_width: int, image_height: int) -> Dict:
        """对提取的文字按位置进行分类"""
        
        # 计算图像分区边界
        left_third = image_width // 3
        right_third = 2 * image_width // 3
        top_third = image_height // 3
        bottom_third = 2 * image_height // 3
        
        # 初始化区域分类（带位置）
        regions = {
            'left_top': [],      # 左上区域
            'left_bottom': [],   # 左下区域
            'center_top': [],    # 中上区域
            'center_bottom': [], # 中下区域
            'right_top': [],     # 右上区域
            'right_bottom': [],  # 右下区域
            'full_width': [],    # 跨区域
            'labels': []         # 按原始顺序保留
        }
        
        # 解析标签类型字段（如"产品名称"、"保质期"等）
        label_keywords = ['产品名称', '型号规格', '生产厂家', '生产日期', '保质期', 
                         '执行标准', '净含量', '使用说明', '注意事项', '检验员', 
                         '产品规格', '参考比', '主剂', '稀释剂', '白水']
        
        for item in text_items:
            text = item['text']
            cx = item['center_x']
            cy = item['center_y']
            
            # 添加原始顺序标签
            item_copy = item.copy()
            regions['labels'].append(item_copy)
            
            # 按位置分类
            is_label = any(kw in text for kw in label_keywords)
            
            if is_label:
                # 标签字段放入相应区域
                if cx < left_third:
                    if cy < top_third:
                        regions['left_top'].append(item)
                    else:
                        regions['left_bottom'].append(item)
                elif cx < right_third:
                    if cy < top_third:
                        regions['center_top'].append(item)
                    else:
                        regions['center_bottom'].append(item)
                else:
                    if cy < top_third:
                        regions['right_top'].append(item)
                    else:
                        regions['right_bottom'].append(item)
            else:
                # 非标签字段放入跨区域
                regions['full_width'].append(item)
        
        logger.info(f"位置分类完成: 上区={len(regions['left_top']) + len(regions['center_top']) + len(regions['right_top'])}, "
                   f"下区={len(regions['left_bottom']) + len(regions['center_bottom']) + len(regions['right_bottom'])}")
        return regions
    
    def classify_regions(self, text: str) -> Dict:
        """对提取的文字进行区域分类（兼容旧版本）"""
        lines = text.split('\n')
        
        regions = {
            'product_name': '',
            'model_spec': '',
            'production_info': [],
            'other_info': []
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if '产品名称' in line:
                regions['product_name'] = line.replace('产品名称：', '').replace('产品名称:', '').strip()
            elif '型号规格' in line:
                regions['model_spec'] = line.replace('型号规格：', '').replace('型号规格:', '').strip()
            elif any(keyword in line for keyword in ['生产', '执行标准', '日期', '保质期', '净含量', '厂家']):
                regions['production_info'].append(line)
            else:
                regions['other_info'].append(line)
        
        logger.info("区域分类完成")
        return regions
    
    def generate_position_map_table(self, regions: Dict, image_width: int, image_height: int, image_index: int = 0) -> str:
        """生成带位置信息的映射表格"""
        table = []
        table.append("=" * 80)
        table.append(f"标签位置映射结果 - 区域 {image_index + 1} (尺寸: {image_width}x{image_height})")
        table.append("=" * 80)
        table.append("{:<8} | {:<20} | {:<8} | {:<8} | {:<8} | {:<8} | {:<6}".format(
            "序号", "文字内容", "X坐标", "Y坐标", "宽度", "高度", "置信度"))
        table.append("-" * 80)
        
        # 按Y坐标排序后输出
        sorted_labels = sorted(regions['labels'], key=lambda x: x['center_y'])
        
        for i, item in enumerate(sorted_labels):
            table.append("{:<8} | {:<20} | {:<8} | {:<8} | {:<8} | {:<8} | {:<6.2f}".format(
                i + 1,
                item['text'][:20],
                item['center_x'],
                item['center_y'],
                item['width'],
                item['height'],
                item['confidence']
            ))
        
        table.append("=" * 80)
        
        # 添加区域分布统计
        table.append("\n区域分布统计:")
        table.append(f"  左上区域: {len(regions['left_top'])} 项")
        table.append(f"  左下区域: {len(regions['left_bottom'])} 项")
        table.append(f"  中上区域: {len(regions['center_top'])} 项")
        table.append(f"  中下区域: {len(regions['center_bottom'])} 项")
        table.append(f"  右上区域: {len(regions['right_top'])} 项")
        table.append(f"  右下区域: {len(regions['right_bottom'])} 项")
        table.append(f"  跨区内容: {len(regions['full_width'])} 项")
        
        return "\n".join(table)
    
    def generate_position_csv(self, regions: Dict, output_path: str, image_index: int = 0):
        """生成带位置信息的CSV文件"""
        import csv
        
        with open(output_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头（仅第一次）
            if image_index == 0 and os.path.getsize(output_path) == 0:
                writer.writerow(['区域编号', '序号', '文字内容', 'X坐标', 'Y坐标', '宽度', '高度', 
                                '左边界', '右边界', '上边界', '下边界', '置信度', '所属区域'])
            
            # 按Y坐标排序
            sorted_labels = sorted(regions['labels'], key=lambda x: x['center_y'])
            
            for i, item in enumerate(sorted_labels):
                # 确定所属区域
                image_width = item['right'] - item['left']
                image_height = item['bottom'] - item['top']
                center_x = item['center_x']
                center_y = item['center_y']
                
                left_third = image_width // 3
                right_third = 2 * image_width // 3
                top_third = image_height // 3
                bottom_third = 2 * image_height // 3
                
                if center_x < left_third:
                    area = '左上' if center_y < top_third else '左下'
                elif center_x < right_third:
                    area = '中上' if center_y < top_third else '中下'
                else:
                    area = '右上' if center_y < top_third else '右下'
                
                writer.writerow([
                    image_index + 1,
                    i + 1,
                    item['text'],
                    item['center_x'],
                    item['center_y'],
                    item['width'],
                    item['height'],
                    item['left'],
                    item['right'],
                    item['top'],
                    item['bottom'],
                    round(item['confidence'], 2),
                    area
                ])
        
        logger.info(f"位置映射 CSV 已保存: {output_path}")
    
    def save_position_visual_map(self, original_image: Image.Image, text_items: List[Dict], output_path: str, image_index: int = 0):
        """保存位置映射可视化图像"""
        # 转换为numpy数组
        img_array = np.array(original_image).copy()
        
        # 按Y坐标排序
        sorted_items = sorted(text_items, key=lambda x: x['center_y'])
        
        # 定义颜色
        colors = [
            (0, 255, 0),    # 绿色
            (255, 0, 0),    # 蓝色
            (0, 255, 255),  # 青色
            (255, 255, 0),  # 黄色
            (255, 0, 255),  # 紫色
            (0, 128, 255),  # 橙色
        ]
        
        # 绘制每个文字区域
        for i, item in enumerate(sorted_items):
            bbox = item['bbox']
            text = item['text']
            color = colors[i % len(colors)]
            
            # 绘制边界框
            pts = np.array(bbox, dtype=np.int32)
            cv2.polylines(img_array, [pts], isClosed=True, color=color, thickness=2)
            
            # 绘制中心点
            cv2.circle(img_array, (item['center_x'], item['center_y']), 5, color, -1)
            
            # 添加文字标签
            label = f"{i + 1}"
            (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            
            # 标签背景
            cv2.rectangle(img_array, 
                         (item['left'], item['top'] - text_height - 10),
                         (item['left'] + text_width + 10, item['top']),
                         color, -1)
            
            # 标签文字
            cv2.putText(img_array, label, 
                       (item['left'] + 5, item['top'] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 转换回PIL图像并保存
        result_image = Image.fromarray(img_array)
        result_image.save(output_path)
        logger.info(f"位置映射可视化图已保存: {output_path}")
    
    def save_excel_style_table(self, text_items: List[Dict], output_path: str, image_index: int = 0):
        """生成Excel样式的表格布局图像"""
        # 按Y坐标排序
        sorted_items = sorted(text_items, key=lambda x: x['center_y'])
        
        # 计算表格尺寸
        n_items = len(sorted_items)
        cell_height = 40
        header_height = 50
        col_widths = [50, 200, 80, 80, 80, 80, 60, 60]
        table_width = sum(col_widths)
        table_height = header_height + n_items * cell_height + 20
        
        # 创建空白图像（白色背景）
        img_array = np.ones((table_height, table_width, 3), dtype=np.uint8) * 255
        
        # 定义颜色
        header_color = (70, 130, 180)  # 钢蓝色
        border_color = (0, 0, 0)
        alt_row_color = (240, 248, 255)  # 淡蓝色
        
        # 绘制表头
        headers = ['序号', '文字内容', 'X', 'Y', '宽度', '高度', '置信度', '区域']
        for j, header in enumerate(headers):
            x1 = sum(col_widths[:j])
            x2 = x1 + col_widths[j]
            # 表头背景
            cv2.rectangle(img_array, (x1, 0), (x2, header_height), header_color, -1)
            # 表头文字
            text = header
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            text_x = x1 + (col_widths[j] - text_w) // 2
            text_y = header_height // 2 + text_h // 2
            cv2.putText(img_array, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # 绘制表头底部边框
        cv2.line(img_array, (0, header_height), (table_width, header_height), border_color, 2)
        
        # 绘制每一行
        colors = [
            (0, 255, 0),    # 绿色
            (255, 0, 0),    # 蓝色
            (0, 255, 255),  # 青色
            (255, 255, 0),  # 黄色
            (255, 0, 255),  # 紫色
            (0, 128, 255),  # 橙色
            (128, 0, 255),  # 紫红
            (0, 255, 128),  # 绿青
        ]
        
        for i, item in enumerate(sorted_items):
            y1 = header_height + i * cell_height
            y2 = y1 + cell_height
            
            # 交替行背景色
            if i % 2 == 1:
                cv2.rectangle(img_array, (0, y1), (table_width, y2), alt_row_color, -1)
            
            # 获取位置颜色
            color = colors[i % len(colors)]
            
            # 确定所属区域
            center_x = item['center_x']
            center_y = item['center_y']
            
            # 绘制行的左边框（带颜色）
            cv2.rectangle(img_array, (0, y1), (5, y2), color, -1)
            
            # 绘制内容
            row_data = [
                str(i + 1),
                item['text'][:20],  # 限制文字长度
                str(item['center_x']),
                str(item['center_y']),
                str(item['width']),
                str(item['height']),
                f"{item['confidence']:.2f}",
                f"({center_x},{center_y})"
            ]
            
            for j, data in enumerate(row_data):
                x1 = sum(col_widths[:j])
                x2 = x1 + col_widths[j]
                
                # 绘制单元格边框
                cv2.rectangle(img_array, (x1, y1), (x2, y2), border_color, 1)
                
                # 绘制文字
                (text_w, text_h), _ = cv2.getTextSize(data, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                text_x = x1 + 5
                text_y = y1 + cell_height // 2 + text_h // 2
                cv2.putText(img_array, data, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            
            # 绘制行底部边框
            cv2.line(img_array, (0, y2), (table_width, y2), border_color, 1)
        
        # 绘制表格边框
        cv2.rectangle(img_array, (0, 0), (table_width, table_height), border_color, 2)
        
        # 保存图像
        result_image = Image.fromarray(img_array)
        result_image.save(output_path)
        logger.info(f"Excel样式表格已保存: {output_path}")
    
    def generate_combined_layout(self, original_image: Image.Image, text_items: List[Dict], 
                                 output_path: str, image_index: int = 0):
        """生成左侧原图+右侧表格的组合布局"""
        # 按Y坐标排序
        sorted_items = sorted(text_items, key=lambda x: x['center_y'])
        
        # 调整原图大小（缩小到合适宽度）
        orig_width = 500
        orig_height = int(original_image.height * orig_width / original_image.width)
        orig_resized = original_image.resize((orig_width, orig_height))
        
        # 生成表格图像
        table_path = output_path.replace('.png', '_table.png')
        self.save_excel_style_table(text_items, table_path, image_index)
        
        # 读取表格图像
        table_image = Image.open(table_path)
        
        # 计算组合图像尺寸
        combined_width = orig_width + table_image.width + 20  # 20像素间隔
        combined_height = max(orig_height, table_image.height)
        
        # 创建组合图像（白色背景）
        combined = Image.new('RGB', (combined_width, combined_height), (255, 255, 255))
        
        # 粘贴原图（带边框）
        border_size = 2
        combined.paste(orig_resized, (border_size, border_size))
        # 绘制原图边框
        for i in range(border_size):
            import PIL.ImageDraw as ImageDraw
            draw = ImageDraw.Draw(combined)
            draw.rectangle([0, 0, orig_width + border_size * 2, orig_height + border_size * 2], 
                          outline=(0, 0, 0), width=border_size)
        
        # 粘贴表格
        combined.paste(table_image, (orig_width + 20, 0))
        
        # 添加标题
        from PIL import ImageDraw
        draw = ImageDraw.Draw(combined)
        title = f"标签 {image_index + 1} 位置映射表"
        draw.text((10, 10), title, fill=(0, 0, 0))
        
        # 保存组合图像
        combined.save(output_path)
        logger.info(f"组合布局图已保存: {output_path}")
        
        # 删除临时表格文件
        import os
        if os.path.exists(table_path):
            os.remove(table_path)
    
    def generate_table(self, regions: Dict, image_index: int = 0) -> str:
        """生成表格化输出"""
        table = []
        table.append("=" * 60)
        table.append(f"标签信息映射结果 - 区域 {image_index + 1}")
        table.append("=" * 60)
        table.append("{:<20} | {:<35}".format("类别", "内容"))
        table.append("-" * 60)
        
        if regions['product_name']:
            table.append("{:<20} | {:<35}".format("产品名称", regions['product_name']))
        
        if regions['model_spec']:
            table.append("{:<20} | {:<35}".format("型号规格", regions['model_spec']))
        
        for info in regions['production_info']:
            table.append("{:<20} | {:<35}".format("生产信息", info))
        
        for info in regions['other_info']:
            table.append("{:<20} | {:<35}".format("其他信息", info))
        
        table.append("=" * 60)
        
        return "\n".join(table)
    
    def generate_csv(self, regions: Dict, output_path: str, image_index: int = 0):
        """生成 CSV 格式输出"""
        import csv
        
        with open(output_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if image_index == 0:
                writer.writerow(['区域编号', '类别', '内容'])
            
            writer.writerow([image_index + 1, '产品名称', regions['product_name']])
            writer.writerow([image_index + 1, '型号规格', regions['model_spec']])
            
            for info in regions['production_info']:
                writer.writerow([image_index + 1, '生产信息', info])
            
            for info in regions['other_info']:
                writer.writerow([image_index + 1, '其他信息', info])
        
        logger.info(f"CSV 文件已追加: {output_path}")
    
    def process(self, output_dir: str = ".", save_debug: bool = False, save_position_map: bool = True) -> List[str]:
        """执行完整的处理流程"""
        results = []
        
        # 1. 查找 BarTender 窗口
        logger.info("正在查找 BarTender 窗口...")
        windows = self.window_recognizer.find_bartender_windows()
        
        if not windows:
            logger.warning("未找到 BarTender 窗口")
            return results
        
        # 2. 处理每个窗口
        for w_idx, window in enumerate(windows):
            logger.info(f"处理窗口 {w_idx + 1}: {window['title']}")
            
            try:
                # 截取窗口
                window_image = self.window_recognizer.capture_window(window['hwnd'])
                
                # 保存原始窗口截图
                window_path = os.path.join(output_dir, f"window_{w_idx + 1}.png")
                window_image.save(window_path)
                logger.info(f"窗口截图已保存: {window_path}")
                
                # 3. 检测白色区域
                logger.info("正在检测白色标签区域...")
                white_regions = self.white_detector.detect_white_regions(window_image, is_full_window=True)
                
                if not white_regions:
                    logger.warning(f"窗口 {w_idx + 1} 中未检测到白色区域")
                    continue
                
                # 保存调试图像
                if save_debug:
                    debug_path = os.path.join(output_dir, f"debug_window_{w_idx + 1}.png")
                    self.white_detector.save_debug_image(window_image, white_regions, debug_path)
                
                # 4. 裁剪白色区域
                logger.info("正在裁剪白色区域...")
                cropped_images = self.white_detector.crop_white_regions(window_image, white_regions)
                
                # 5. 处理每个白色区域
                for i, cropped in enumerate(cropped_images):
                    # 保存裁剪的标签图像
                    label_path = os.path.join(output_dir, f"label_{w_idx + 1}_{i + 1}.png")
                    cropped.save(label_path)
                    logger.info(f"标签图像已保存: {label_path}")
                    
                    # OCR 提取文字及位置
                    logger.info(f"正在提取标签 {w_idx + 1}-{i + 1} 的文字及位置...")
                    text_items = self.extract_text_from_image(cropped)
                    
                    if not text_items:
                        logger.warning(f"标签 {w_idx + 1}-{i + 1} 未提取到文字")
                        continue
                    
                    # 位置分类
                    regions = self.classify_regions_with_position(text_items, cropped.width, cropped.height)
                    
                    # 保存位置映射可视化图
                    vis_path = os.path.join(output_dir, f"position_map_{w_idx + 1}_{i + 1}.png")
                    self.save_position_visual_map(cropped, text_items, vis_path, i)
                    
                    # 生成组合布局图（原图+Excel表格）
                    combined_path = os.path.join(output_dir, f"combined_layout_{w_idx + 1}_{i + 1}.png")
                    self.generate_combined_layout(cropped, text_items, combined_path, i)
                    
                    # 生成位置映射表格
                    if save_position_map:
                        pos_table = self.generate_position_map_table(regions, cropped.width, cropped.height, i)
                        results.append(pos_table)
                        print(f"\n{pos_table}")
                        
                        # 生成位置映射CSV
                        pos_csv_path = os.path.join(output_dir, "position_map_result.csv")
                        self.generate_position_csv(regions, pos_csv_path, i)
                    
                    # 生成内容表格（兼容）
                    text_combined = '\n'.join([item['text'] for item in text_items])
                    simple_regions = self.classify_regions(text_combined)
                    table = self.generate_table(simple_regions, i)
                    results.append(table)
                    
                    # 生成CSV
                    csv_path = os.path.join(output_dir, "labels_result.csv")
                    self.generate_csv(simple_regions, csv_path, i)
                
            except Exception as e:
                logger.error(f"处理窗口 {w_idx + 1} 失败: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BarTender 标签信息映射程序')
    parser.add_argument('-o', '--output', default='.', help='输出目录')
    parser.add_argument('--debug', action='store_true', help='保存调试图像')
    parser.add_argument('--no-position-map', action='store_true', help='不保存位置映射')
    parser.add_argument('--no-window', action='store_true', help='不截取窗口，直接处理图片文件')
    parser.add_argument('input', nargs='?', help='输入图片文件或目录（使用 --no-window 时需要）')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    mapper = BartenderInfoMapper()
    
    if args.no_window:
        # 直接处理图片文件
        if not args.input:
            print("错误: 使用 --no-window 参数时需要指定输入文件或目录")
            sys.exit(1)
        
        if os.path.isfile(args.input):
            from PIL import Image
            image = Image.open(args.input)
            
            # 提取文字及位置
            text_items = mapper.extract_text_from_image(image)
            
            if not text_items:
                print("未提取到文字")
                sys.exit(1)
            
            # 位置分类
            regions = mapper.classify_regions_with_position(text_items, image.width, image.height)
            
            # 生成位置映射表格
            if not args.no_position_map:
                pos_table = mapper.generate_position_map_table(regions, image.width, image.height)
                print(f"\n{pos_table}")
                
                # 保存位置映射CSV
                csv_path = os.path.join(args.output, "position_map_result.csv")
                mapper.generate_position_csv(regions, csv_path)
        else:
            print("目录处理暂不支持 --no-window 模式")
    else:
        # 正常模式：识别窗口并处理
        save_position_map = not args.no_position_map
        results = mapper.process(output_dir=args.output, save_debug=args.debug, save_position_map=save_position_map)
        
        if results:
            print(f"\n结果已保存到: {args.output}")
        else:
            print("未找到任何标签信息")


if __name__ == "__main__":
    main()