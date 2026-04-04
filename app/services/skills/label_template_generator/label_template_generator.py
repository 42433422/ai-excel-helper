# -*- coding: utf-8 -*-
"""
Label Template Generator - 从图片生成标签模板代码

基于参考图片，使用 PIL (Pillow) 库分析并生成对应的 Python 标签模板代码。
支持 OCR 识别固定标签和可变数据。
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from PIL import Image

logger = logging.getLogger(__name__)


def analyze_image(image_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    分析图片并提取基本信息

    Args:
        image_path: 图片文件路径
        verbose: 是否输出详细信息

    Returns:
        包含图片分析结果的字典
    """
    try:
        img = Image.open(image_path)
        width, height = img.size

        result = {
            "success": True,
            "file": Path(image_path).name,
            "format": img.format,
            "mode": img.mode,
            "size": {
                "width": width,
                "height": height
            },
            "colors": _analyze_colors(img),
            "sections": _estimate_sections(width, height)
        }

        if verbose:
            result["additional_info"] = {
                "dpi": img.info.get("dpi", "unknown"),
                "has_transparency": img.mode in ("RGBA", "LA"),
                "estimated_font_sizes": _estimate_font_sizes(width, height)
            }

        return result

    except FileNotFoundError:
        return {
            "success": False,
            "error": f"文件不存在：{image_path}"
        }
    except Exception as e:
        logger.error(f"分析图片失败：{e}")
        return {
            "success": False,
            "error": f"分析失败：{str(e)}"
        }


def extract_text_with_ocr(image_path: str, use_regions: bool = True) -> Dict[str, Any]:
    """
    使用 PaddleOCR 提取图片中的文本，并识别固定标签和可变数据
    
    Args:
        image_path: 图片文件路径
        use_regions: 是否使用分区域识别（提高准确率）
    """
    try:
        from PIL import Image
        import numpy as np
        import cv2

        img = Image.open(image_path)
        width, height = img.size

        # 1. 先检测网格布局（表格线）- 直接检测连续的黑色线条
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # 二值化：只检测非常黑的像素（表格边框），避免检测到文字
        # 文字通常不是纯黑，而表格边框是纯黑 (#000000)
        _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        
        # 检测水平线：扫描每一行，查找连续的黑色线段
        horizontal_lines = []
        for y in range(gray.shape[0]):
            row = binary[y, :]
            # 查找连续线段
            continuous_start = None
            max_continuous_length = 0
            current_length = 0
            
            for x in range(len(row)):
                if row[x] > 0:  # 黑色像素
                    if continuous_start is None:
                        continuous_start = x
                    current_length += 1
                else:
                    if current_length > max_continuous_length:
                        max_continuous_length = current_length
                    continuous_start = None
                    current_length = 0
            
            # 检查最后一段
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            
            # 如果最长连续线段超过图片宽度的 50%，认为是表格线
            if max_continuous_length > gray.shape[1] * 0.5:
                horizontal_lines.append(y)
        
        # 检测垂直线：扫描每一列，查找连续的黑色线段
        vertical_lines = []
        for x in range(gray.shape[1]):
            col = binary[:, x]
            continuous_start = None
            max_continuous_length = 0
            current_length = 0
            
            for y in range(len(col)):
                if col[y] > 0:  # 黑色像素
                    if continuous_start is None:
                        continuous_start = y
                    current_length += 1
                else:
                    if current_length > max_continuous_length:
                        max_continuous_length = current_length
                    continuous_start = None
                    current_length = 0
            
            # 检查最后一段
            if current_length > max_continuous_length:
                max_continuous_length = current_length
            
            # 如果最长连续线段超过图片高度的 50%，认为是表格线
            if max_continuous_length > gray.shape[0] * 0.5:
                vertical_lines.append(x)
        
        # 去重并排序
        horizontal_lines = sorted(list(set([int(y) for y in horizontal_lines])))
        vertical_lines = sorted(list(set([int(x) for x in vertical_lines])))
        
        # 合并相近的线条（表格线通常间距较大）
        def merge_close_lines(lines, threshold=50):
            if not lines:
                return []
            merged = [lines[0]]
            for line in lines[1:]:
                if line - merged[-1] > threshold:
                    merged.append(line)
            return merged
        
        # 先合并粗边框导致的相邻线条（距离 < 5 像素的）
        def merge_very_close_lines(lines, threshold=5):
            if not lines:
                return []
            merged = [lines[0]]
            for line in lines[1:]:
                if line - merged[-1] > threshold:
                    merged.append(line)
                else:
                    # 取中间值作为合并后的位置
                    merged[-1] = (merged[-1] + line) // 2
            return merged
        
        horizontal_lines = merge_very_close_lines(horizontal_lines, threshold=5)
        vertical_lines = merge_very_close_lines(vertical_lines, threshold=5)
        
        # 再合并间距较大的线条（真正的分隔线）
        horizontal_lines = merge_close_lines(horizontal_lines, threshold=50)
        vertical_lines = merge_close_lines(vertical_lines, threshold=50)
        
        logger.info(f"检测到网格：{len(horizontal_lines)}条水平线，{len(vertical_lines)}条垂直线")

        # 2. OCR 识别（与 /api/ocr 共用 OCRService：默认 PaddleOCR，可回退 EasyOCR）
        from app.services.ocr_service import get_ocr_service

        ocr_svc = get_ocr_service()
        text_blocks = ocr_svc.recognize_text_blocks(img)
        if not text_blocks:
            return {
                "success": False,
                "error": "OCR 未识别到文本。请安装 paddlepaddle+paddleocr（推荐）或 easyocr，并检查图片清晰度。",
                "fallback_fields": _extract_fields_by_pattern(image_path),
            }

        logger.info("OCR 识别到 %s 个文本块（引擎：%s）", len(text_blocks), ocr_svc.get_active_ocr_backend())

        # 构建网格单元格信息
        cells = []
        merged_cells = []

        if len(horizontal_lines) > 1 and len(vertical_lines) > 1:
            rows = len(horizontal_lines) - 1
            cols = len(vertical_lines) - 1

            # 第一步：构建基础单元格并检测边框缺失
            for i in range(rows):
                for j in range(cols):
                    x = vertical_lines[j]
                    y = horizontal_lines[i]
                    w = vertical_lines[j + 1] - vertical_lines[j]
                    h = horizontal_lines[i + 1] - horizontal_lines[i]

                    cell = {
                        'row': i,
                        'col': j,
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'should_merge_right': False
                    }

                    # 检测右侧边框是否缺失（水平合并）
                    # 注意：只有当右侧单元格存在但边框缺失时才标记为合并
                    if j < cols - 1:
                        right_border_x = x + w
                        border_black_count = 0
                        border_total = 0

                        for check_y in range(y, y + h):
                            if check_y < gray.shape[0] and right_border_x < gray.shape[1]:
                                border_total += 1
                                if binary[check_y, right_border_x] > 0:
                                    border_black_count += 1

                        # 只有当边框有像素但少于50%时才认为是边框缺失
                        # 如果边框完全没有像素(0%)，说明是空列，不是合并
                        if border_total > 0 and 0 < border_black_count < h * 0.5:
                            cell['should_merge_right'] = True

                    cells.append(cell)

            # 第二步：实际合并单元格
            merged_cells = []
            visited = set()

            for i in range(rows):
                for j in range(cols):
                    cell_id = f"{i},{j}"
                    if cell_id in visited:
                        continue

                    cell = next((c for c in cells if c['row'] == i and c['col'] == j), None)
                    if not cell:
                        continue

                    # 计算向右合并多少列
                    merge_count = 1
                    while cell['should_merge_right'] and j + merge_count < cols:
                        visited.add(f"{i},{j + merge_count}")
                        merge_count += 1
                        if j + merge_count < cols:
                            next_cell = next((c for c in cells if c['row'] == i and c['col'] == j + merge_count), None)
                            if next_cell:
                                cell = next_cell
                            else:
                                break

                    # 计算合并后的位置和尺寸
                    merged_cells.append({
                        'row': i,
                        'start_col': j,
                        'end_col': j + merge_count - 1,
                        'merge_cols': merge_count,
                        'x': vertical_lines[j],
                        'y': horizontal_lines[i],
                        'width': vertical_lines[j + merge_count] - vertical_lines[j],
                        'height': horizontal_lines[i + 1] - horizontal_lines[i],
                        'original_cols': list(range(j, j + merge_count))
                    })

                    visited.add(cell_id)

        # 构建合并单元格信息（只包含真正合并的单元格，即 start_col != end_col）
        merged_cells_info = []
        for mc in merged_cells:
            if mc.get('start_col', 0) != mc.get('end_col', 0):
                merged_cells_info.append({
                    'row': mc['row'],
                    'start_col': mc['start_col'],
                    'end_col': mc['end_col']
                })

        # 4. 基于网格布局智能配对字段
        fields = _pair_fields_by_grid(text_blocks, horizontal_lines, vertical_lines, merged_cells_info)

        # 5. 返回结果 - 使用合并后的单元格用于 grid 返回
        return {
            "success": True,
            "text_blocks": text_blocks,
            "fields": fields,
            "total_blocks": len(text_blocks),
            "grid": {
                "rows": len(horizontal_lines) - 1 if len(horizontal_lines) > 1 else 0,
                "cols": len(vertical_lines) - 1 if len(vertical_lines) > 1 else 0,
                "horizontal_lines": horizontal_lines,
                "vertical_lines": vertical_lines,
                "cells": merged_cells if merged_cells else cells
            }
        }

    except ImportError as e:
        logger.warning("标签模板 OCR 依赖缺失：%s", e)
        return {
            "success": False,
            "error": f"缺少图像处理依赖：{e}（需 Pillow、numpy、opencv-python；OCR 需 paddleocr 或 easyocr）",
            "fallback_fields": _extract_fields_by_pattern(image_path),
        }
    except Exception as e:
        logger.error(f"OCR 提取失败：{e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"OCR 失败：{str(e)}",
            "fallback_fields": _extract_fields_by_pattern(image_path)
        }


def _pair_fields_by_grid(text_blocks: List[Dict], horizontal_lines: List[int], vertical_lines: List[int], merged_horizontal: List[Dict] = None) -> List[Dict[str, Any]]:
    """
    基于网格布局智能配对字段（标签 + 值）

    Args:
        text_blocks: OCR 识别的文本块列表
        horizontal_lines: 水平线 Y 坐标列表
        vertical_lines: 垂直线 X 坐标列表
        merged_horizontal: 水平合并单元格列表

    Returns:
        字段列表
    """
    if not text_blocks:
        return []

    if merged_horizontal is None:
        merged_horizontal = []

    # 1. 按 Y 坐标排序文本块
    text_blocks_sorted = sorted(text_blocks, key=lambda x: x['y_center'])

    # 2. 根据网格线确定每个文本块属于哪个单元格
    def find_cell(x, y, h_lines, v_lines):
        """根据坐标找到单元格索引"""
        row = 0
        for i in range(len(h_lines) - 1):
            if h_lines[i] <= y < h_lines[i + 1]:
                row = i
                break

        col = 0
        for j in range(len(v_lines) - 1):
            if v_lines[j] <= x < v_lines[j + 1]:
                col = j
                break

        return row, col

    # 3. 为每个文本块分配单元格
    for block in text_blocks_sorted:
        center_x = block['center'][0]
        center_y = block['center'][1]
        row, col = find_cell(center_x, center_y, horizontal_lines, vertical_lines)
        block['cell_row'] = row
        block['cell_col'] = col

    # 4. 按行分组
    def group_by_row(blocks, h_lines):
        groups = []
        current_group = []
        current_row = None

        for block in blocks:
            row = block['cell_row']
            if current_row is None or row == current_row:
                current_group.append(block)
                current_row = row
            else:
                groups.append({'row': current_row, 'blocks': current_group})
                current_group = [block]
                current_row = row

        if current_group:
            groups.append({'row': current_row, 'blocks': current_group})

        return groups

    row_groups = group_by_row(text_blocks_sorted, horizontal_lines)

    # 5. 同一行内，按 X 坐标排序并配对
    fields = []
    for group in row_groups:
        blocks = group['blocks']
        # 同一行内按 X 坐标排序
        blocks_sorted = sorted(blocks, key=lambda x: x['left'])

        # 检查这一行是否有合并单元格
        row = group['row']
        row_merges = [m for m in merged_horizontal if m.get('row') == row]

        # 配对：标签 + 值
        j = 0
        while j < len(blocks_sorted):
            block = blocks_sorted[j]
            col = block['cell_col']

            # 检查这个块是否在合并单元格的范围内
            is_in_merged = False
            merged_info = None
            for m in row_merges:
                if m.get('start_col') <= col <= m.get('end_col'):
                    is_in_merged = True
                    merged_info = m
                    break

            if is_in_merged and col == merged_info.get('start_col'):
                # 这是合并单元格的起始
                field_type, field_key = _classify_field(block['text'])

                fields.append({
                    'label': block['text'],
                    'value': '',
                    'field_key': field_key,
                    'type': field_type,
                    'position': {
                        'left': block['left'],
                        'top': block['top'],
                        'width': block['width'],
                        'height': block['height']
                    },
                    'full_text': block['text'],
                    'confidence': block['conf'],
                    'is_merged': True,
                    'merge_cols': merged_info.get('end_col', merged_info.get('start_col')) - merged_info.get('start_col') + 1
                })

                # 跳过合并单元格范围内的其他块
                # 计算需要跳过的块数
                skip_count = merged_info.get('end_col', col) - col
                j += skip_count

            elif not is_in_merged:
                # 普通单元格（不在任何合并单元格范围内）
                if j + 1 < len(blocks_sorted):
                    next_block = blocks_sorted[j + 1]
                    next_col = next_block['cell_col']

                    # 检查下一个块是否在合并单元格范围内
                    next_is_in_merged = False
                    for m in row_merges:
                        if m.get('start_col') <= next_col <= m.get('end_col'):
                            next_is_in_merged = True
                            break

                    # 只有当下一个块不在合并单元格范围内且是相邻列时，才进行配对
                    if not next_is_in_merged and next_col == col + 1:
                        label_block = block
                        value_block = next_block
                        field_type, field_key = _classify_field(label_block['text'])

                        fields.append({
                            'label': label_block['text'],
                            'value': value_block['text'],
                            'field_key': field_key,
                            'type': field_type,
                            'position': {
                                'left': label_block['left'],
                                'top': label_block['top'],
                                'width': label_block['width'],
                                'height': label_block['height']
                            },
                            'full_text': f"{label_block['text']}: {value_block['text']}",
                            'confidence': (label_block['conf'] + value_block['conf']) / 2,
                            'is_merged': False
                        })
                        j += 1
                    else:
                        # 下一个块在合并单元格范围内或是单独块
                        field_type, field_key = _classify_field(block['text'])
                        fields.append({
                            'label': block['text'],
                            'value': '',
                            'field_key': field_key,
                            'type': field_type,
                            'position': {
                                'left': block['left'],
                                'top': block['top'],
                                'width': block['width'],
                                'height': block['height']
                            },
                            'full_text': block['text'],
                            'confidence': block['conf'],
                            'is_merged': False
                        })
                else:
                    field_type, field_key = _classify_field(block['text'])
                    fields.append({
                        'label': block['text'],
                        'value': '',
                        'field_key': field_key,
                        'type': field_type,
                        'position': {
                            'left': block['left'],
                            'top': block['top'],
                            'width': block['width'],
                            'height': block['height']
                        },
                        'full_text': block['text'],
                        'confidence': block['conf'],
                        'is_merged': False
                    })

            # else: 在合并单元格范围内但不是起始，跳过

            j += 1

    return fields


def _classify_field(label: str) -> Tuple[str, str]:
    """
    判断字段类型（固定标签 or 可变数据）和字段 key
    
    Returns:
        (field_type, field_key)
    """
    common_labels = {
        '品名': 'product_name',
        '颜色': 'color',
        '货号': 'item_number',
        '码段': 'code_segment',
        '等级': 'grade',
        '执行标准': 'standard',
        '统一零售价': 'price',
        '产品名称': 'product_name',
        '产品编号': 'product_number',
        '规格': 'specification',
        '型号': 'model',
        '价格': 'price',
        '零售价': 'price',
        '生产日期': 'production_date',
        '保质期': 'shelf_life',
        '产品规格': 'product_spec',
        '检验员': 'inspector'
    }
    
    # 检查是否是固定标签
    if label in common_labels:
        return 'fixed_label', common_labels[label]
    elif label.endswith('价'):
        return 'fixed_label', 'price'
    else:
        return 'dynamic', label


def _identify_fields(text_blocks: List[Dict]) -> List[Dict[str, Any]]:
    """
    识别文本块中的字段（固定标签和可变数据）
    
    常见固定标签模式：
    - 品名：、颜色：、货号：、码段：、等级：、执行标准：、统一零售价：
    - 产品名称、产品编号、规格、型号、等级
    - 无冒号格式：产品编号 6808AA、产品名称 PE 封固底漆稀料
    """
    fields = []
    common_labels = {
        '品名': 'product_name',
        '颜色': 'color',
        '货号': 'item_number',
        '码段': 'code_segment',
        '等级': 'grade',
        '执行标准': 'standard',
        '统一零售价': 'price',
        '产品名称': 'product_name',
        '产品编号': 'product_number',
        '规格': 'specification',
        '型号': 'model',
        '价格': 'price',
        '零售价': 'price',
        '生产日期': 'production_date',
        '保质期': 'shelf_life',
        '产品规格': 'product_spec',
        '检验员': 'inspector'
    }
    
    for block in text_blocks:
        text = block['text']
        
        # 匹配 "标签：值" 或 "标签：值" 模式（带冒号）
        match = re.match(r'^([^:：]+)[:：]\s*(.*)$', text)
        if match:
            label = match.group(1).strip()
            value = match.group(2).strip()
            
            # 确定字段类型
            field_type = 'dynamic'  # 默认可变数据
            
            # 检查是否是固定标签
            if label in common_labels:
                field_key = common_labels[label]
                field_type = 'fixed_label'  # 固定标签
            elif label.endswith('价'):
                field_key = 'price'
                field_type = 'fixed_label'
            else:
                field_key = label
            
            fields.append({
                'label': label,
                'value': value,
                'field_key': field_key,
                'type': field_type,
                'position': {
                    'left': block['left'],
                    'top': block['top'],
                    'width': block['width'],
                    'height': block['height']
                },
                'full_text': text,
                'confidence': block['conf']
            })
        
        # 匹配无冒号格式："产品编号 6808AA" 类型
        else:
            for known_label in common_labels.keys():
                if text.startswith(known_label):
                    value_part = text[len(known_label):].strip()
                    if value_part:
                        field_key = common_labels[known_label]
                        fields.append({
                            'label': known_label,
                            'value': value_part,
                            'field_key': field_key,
                            'type': 'fixed_label' if known_label in ['产品名称', '产品编号', '规格', '生产日期', '保质期', '产品规格', '检验员'] else 'dynamic',
                            'position': {
                                'left': block['left'],
                                'top': block['top'],
                                'width': block['width'],
                                'height': block['height']
                            },
                            'full_text': text,
                            'confidence': block['conf']
                        })
                    break
    
    return fields


def _extract_fields_by_pattern(image_path: str) -> List[Dict[str, Any]]:
    """
    基于常见标签模式提取字段（OCR 不可用时的回退方案）
    """
    # 这是一个简化的回退方案，实际应该使用 OCR
    return [
        {'label': '品名', 'value': '（需要 OCR 识别）', 'field_key': 'product_name', 'type': 'fixed_label'},
        {'label': '颜色', 'value': '（需要 OCR 识别）', 'field_key': 'color', 'type': 'fixed_label'},
        {'label': '货号', 'value': '（需要 OCR 识别）', 'field_key': 'item_number', 'type': 'fixed_label'},
        {'label': '码段', 'value': '（需要 OCR 识别）', 'field_key': 'code_segment', 'type': 'fixed_label'},
        {'label': '等级', 'value': '（需要 OCR 识别）', 'field_key': 'grade', 'type': 'fixed_label'},
        {'label': '执行标准', 'value': '（需要 OCR 识别）', 'field_key': 'standard', 'type': 'fixed_label'},
        {'label': '统一零售价', 'value': '（需要 OCR 识别）', 'field_key': 'price', 'type': 'fixed_label'}
    ]


def _analyze_colors(img: Image.Image) -> Dict[str, Any]:
    """分析图片中的主要颜色"""
    try:
        img_rgb = img.convert("RGB")
        
        corners = [
            (10, 10),
            (img.width - 10, 10),
            (10, img.height - 10),
            (img.width - 10, img.height - 10)
        ]
        
        corner_colors = [img_rgb.getpixel(pos) for pos in corners]
        
        bg_color = corner_colors[0]
        is_consistent_bg = all(c == bg_color for c in corner_colors)
        
        return {
            "background": f"#{bg_color[0]:02x}{bg_color[1]:02x}{bg_color[2]:02x}",
            "is_consistent_background": is_consistent_bg,
            "border": "#000000",
            "text": "#000000"
        }
    except:
        return {
            "background": "#FFFFFF",
            "is_consistent_background": True,
            "border": "#000000",
            "text": "#000000"
        }


def _estimate_sections(width: int, height: int) -> List[Dict[str, Any]]:
    """估算标签的分区"""
    sections = []
    
    if width >= 800 and height >= 500:
        sections = [
            {"name": "product_number", "y_start": 20, "y_end": 100, "description": "产品编号区域"},
            {"name": "product_name", "y_start": 110, "y_end": 190, "description": "产品名称区域"},
            {"name": "ratio", "y_start": 200, "y_end": 290, "description": "参考配比区域"},
            {"name": "date_spec", "y_start": 300, "y_end": 380, "description": "日期和规格区域"},
            {"name": "footer", "y_start": 390, "y_end": 460, "description": "底部提示区域"}
        ]
    elif width >= 400 and height >= 300:
        sections = [
            {"name": "header", "y_start": 20, "y_end": 80, "description": "标题区域"},
            {"name": "content", "y_start": 90, "y_end": 220, "description": "内容区域"},
            {"name": "footer", "y_start": 230, "y_end": 280, "description": "底部区域"}
        ]
    else:
        sections = [
            {"name": "main", "y_start": 10, "y_end": height - 10, "description": "主内容区域"}
        ]
    
    return sections


def _estimate_font_sizes(width: int, height: int) -> Dict[str, int]:
    """估算字体大小"""
    if width >= 800:
        return {
            "title": 70,
            "label": 40,
            "content": 58,
            "small": 38
        }
    elif width >= 400:
        return {
            "title": 40,
            "label": 24,
            "content": 32,
            "small": 20
        }
    else:
        return {
            "title": 24,
            "label": 14,
            "content": 18,
            "small": 12
        }


def generate_template_code(
    image_path: str,
    class_name: str = "LabelTemplateGenerator",
    ocr_result: Optional[Dict] = None,
    verbose: bool = False
) -> str:
    """
    从图片生成 Python 模板代码

    Args:
        image_path: 图片文件路径
        class_name: 生成的类名
        ocr_result: OCR 识别结果（可选）
        verbose: 是否生成详细代码

    Returns:
        生成的 Python 代码字符串
    """
    analysis = analyze_image(image_path, verbose=True)
    
    if not analysis["success"]:
        return f"# Error: {analysis.get('error', '分析失败')}"

    width = analysis["size"]["width"]
    height = analysis["size"]["height"]
    colors = analysis["colors"]
    
    # 如果有 OCR 结果，生成更智能的代码
    if ocr_result and ocr_result.get('success'):
        fields = ocr_result.get('fields', [])
        code = _generate_code_with_fields(image_path, class_name, width, height, colors, fields)
    else:
        code = _generate_basic_code(image_path, class_name, width, height, colors)
    
    return code


def _generate_code_with_fields(
    image_path: str,
    class_name: str,
    width: int,
    height: int,
    colors: Dict,
    fields: List[Dict]
) -> str:
    """基于 OCR 识别的字段生成代码"""
    
    analysis = analyze_image(image_path)
    code = f'''# -*- coding: utf-8 -*-
"""
{class_name} - 标签模板生成器

此代码由 label-template-generator 自动生成，基于图片: {analysis["file"]}
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

固定标签和可变数据字段已自动识别。
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class {class_name}:
    """标签模板生成器类 - 支持动态数据填充"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.width = {width}
        self.height = {height}
        self.bg_color = "{colors["background"]}"
        self.border_color = "{colors["border"]}"
        self.text_color = "{colors["text"]}"
        self.output_dir = output_dir or os.getcwd()
        
        # 定义固定标签和对应的字段
        self.fields = {{
'''
    
    # 添加识别到的字段
    for field in fields:
        field_key = field.get('field_key', field['label'])
        label = field['label']
        value = field.get('value', '')
        field_type = field.get('type', 'dynamic')
        
        code += f'''            "{field_key}": {{
                "label": "{label}",
                "default_value": "{value}",
                "type": "{field_type}",
                "editable": {True if field_type == 'fixed_label' else False}
            }},
'''
    
    code += '''        }
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取中文字体"""
        import platform
        
        font_paths = []
        
        if platform.system() == "Windows":
            font_paths = [
                "C:\\\\Windows\\\\Fonts\\\\simhei.ttf",
                "C:\\\\Windows\\\\Fonts\\\\msyh.ttc",
                "C:\\\\Windows\\\\Fonts\\\\simsun.ttc",
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
                   例如：{{
                       "product_name": "XX 运动鞋",
                       "color": "白色",
                       "item_number": "1635",
                       "code_segment": "00001",
                       "grade": "合格品",
                       "standard": "QB/T4331-2013",
                       "price": "199"
                   }}
            order_number: 订单号（可选）
            label_index: 标签序号
            
        Returns:
            生成的文件名，失败返回 None
        """
        try:
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)
            
            self._draw_border(draw)
            self._draw_fields(draw, data)
            
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 生成文件名
            product_name = data.get('product_name', data.get('item_number', 'label'))
            safe_name = str(product_name).replace("/", "_").replace(" ", "_")[:20]
            
            if order_number:
                filename = f"{{order_number}}_第{{label_index}}项_{{safe_name}}.png"
            else:
                filename = f"label_{{safe_name}}_{{datetime.now().strftime('%Y%m%d%H%M%S')}}.png"
            
            output_path = os.path.join(self.output_dir, filename)
            image.save(output_path)
            logger.info(f"标签已生成：{{output_path}}")
            return filename
            
        except Exception as e:
            logger.error(f"生成标签失败：{{e}}")
            return None
    
    def _draw_border(self, draw: ImageDraw.ImageDraw):
        """绘制边框"""
        draw.rectangle([0, 0, self.width - 1, self.height - 1], outline=self.border_color, width=3)
    
    def _draw_fields(self, draw: ImageDraw.ImageDraw, data: Dict[str, Any]):
        """绘制所有字段"""
        y_offset = 40
        line_height = 50
        
        label_font = self._get_font(36)
        value_font = self._get_font(40)
        bold_font = self._get_font(48)
        
        # 遍历所有字段并绘制
        for field_key, field_info in self.fields.items():
            label = field_info['label']
            value = data.get(field_key, field_info.get('default_value', ''))
            
            # 特殊处理价格字段
            if field_key == 'price':
                draw.text((40, y_offset), f"统一零售价：¥ ", font=label_font, fill=self.text_color)
                draw.text((220, y_offset), str(value), font=bold_font, fill=self.text_color)
            else:
                draw.text((40, y_offset), f"{{label}}: ", font=label_font, fill=self.text_color)
                draw.text((180, y_offset), str(value), font=value_font, fill=self.text_color)
            
            y_offset += line_height
        
        # 绘制条形码
        y_offset += 20
        self._draw_barcode(draw, data, y_offset)
    
    def _draw_barcode(self, draw: ImageDraw.ImageDraw, data: Dict[str, Any], y_offset: int):
        """绘制条形码"""
        try:
            # 确定条码数据
            barcode_data = None
            if data.get('barcode_data'):
                barcode_data = str(data.get('barcode_data'))
            elif data.get('auto_barcode', False):
                # 自动组合条码数据：货号 + 码段
                item_number = str(data.get('item_number', ''))
                code_segment = str(data.get('code_segment', ''))
                if item_number and code_segment:
                    barcode_data = f"{{item_number}}{{code_segment}}"
                elif item_number:
                    barcode_data = item_number
            
            if barcode_data:
                # 使用 barcode 库生成条形码
                from barcode import Code128, EAN13, Code39
                from barcode.writer import ImageWriter
                from io import BytesIO
                
                # 根据数据选择合适的条码类型
                if barcode_data.isdigit() and len(barcode_data) >= 12:
                    BarcodeClass = EAN13
                    # EAN-13 需要 12 位数据
                    barcode_value = barcode_data[:12].ljust(12, '0')
                else:
                    BarcodeClass = Code128
                    barcode_value = barcode_data
                
                # 生成条码
                barcode = BarcodeClass(barcode_value, writer=ImageWriter())
                
                # 保存到 BytesIO
                buffer = BytesIO()
                barcode.write(buffer, options={{
                    'module_width': 2,
                    'module_height': 40,
                    'font_size': 10,
                    'text_distance': 5,
                    'show_text': True
                }})
                buffer.seek(0)
                
                # 转换为 PIL Image 并绘制
                from PIL import Image
                barcode_img = Image.open(buffer)
                
                # 计算居中位置
                barcode_width = 360
                x_offset = (self.width - barcode_width) // 2
                
                # 粘贴条码到标签上
                self.image.paste(barcode_img, (x_offset, y_offset))
            else:
                # 无条码数据时绘制占位符
                draw.rectangle([40, y_offset, self.width - 40, y_offset + 80], outline=self.border_color, width=1)
                draw.text((self.width // 2 - 60, y_offset + 90), "无条码数据", font=self._get_font(20), fill=self.text_color)
                
        except ImportError:
            # python-barcode 未安装时绘制占位符
            draw.rectangle([40, y_offset, self.width - 40, y_offset + 80], outline=self.border_color, width=1)
            draw.text((self.width // 2 - 60, y_offset + 90), "1txm.com", font=self._get_font(20), fill=self.text_color)
        except Exception as e:
            logger.error(f"绘制条码失败：{{e}}")
            draw.rectangle([40, y_offset, self.width - 40, y_offset + 80], outline=self.border_color, width=1)
    
    def get_field_template(self) -> Dict[str, Any]:
        """
        获取字段模板，用于显示哪些是固定标签，哪些是可编辑数据
        
        Returns:
            字段模板字典
        """
        return {{
            field_key: {{
                "label": info["label"],
                "type": info["type"],
                "editable": info["editable"],
                "example_value": info.get("default_value", "")
            }}
            for field_key, info in self.fields.items()
        }}


def example_usage():
    """使用示例"""
    generator = {class_name}(output_dir="./labels")
    
    # 示例数据 - 这些是可变的值
    data = {{
        "product_name": "XX 运动鞋",
        "color": "白色",
        "item_number": "1635",
        "code_segment": "00001",
        "grade": "合格品",
        "standard": "QB/T4331-2013",
        "price": "199",
        # 条形码数据（可选）
        "auto_barcode": True  # 自动组合 item_number + code_segment 生成条码
        # 或者使用自定义条码数据:
        # "barcode_data": "163500001"
    }}
    
    filename = generator.generate_label(data, "ORDER-001", 1)
    print(f"生成的标签：{{filename}}")
    
    # 查看字段模板
    template = generator.get_field_template()
    print("\\n字段模板:")
    for key, info in template.items():
        print(f"  {{key}}: {{info}}")


if __name__ == "__main__":
    example_usage()
'''
    
    return code


def _generate_basic_code(image_path: str, class_name: str, width: int, height: int, colors: Dict) -> str:
    """生成基础代码（无 OCR 时使用）"""
    analysis = analyze_image(image_path)
    
    code = f'''# -*- coding: utf-8 -*-
"""
{class_name} - 标签模板生成器

此代码由 label-template-generator 自动生成，基于图片：{analysis["file"]}
生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class {class_name}:
    """标签模板生成器类"""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.width = {width}
        self.height = {height}
        self.bg_color = "{colors["background"]}"
        self.border_color = "{colors["border"]}"
        self.text_color = "{colors["text"]}"
        self.output_dir = output_dir or os.getcwd()
        
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取中文字体"""
        import platform
        
        font_paths = []
        
        if platform.system() == "Windows":
            font_paths = [
                "C:\\\\Windows\\\\Fonts\\\\simhei.ttf",
                "C:\\\\Windows\\\\Fonts\\\\msyh.ttc",
                "C:\\\\Windows\\\\Fonts\\\\simsun.ttc",
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
            filename = f"{{order_number}}_第{{label_index}}项_{{safe_name}}.png"
            output_path = os.path.join(self.output_dir, filename)
            image.save(output_path)
            logger.info(f"标签已生成：{{output_path}}")
            return filename
            
        except Exception as e:
            logger.error(f"生成标签失败：{{e}}")
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
                labels.append({{
                    "filename": filename,
                    "order_number": order_number,
                    "label_index": i
                }})
        return labels


def example_usage():
    """使用示例"""
    generator = {class_name}(output_dir="./labels")
    
    product = {{
        "product_name": "示例产品",
        "item_number": "12345",
        "grade": "合格品"
    }}
    
    filename = generator.generate_label(product, "ORDER-001", 1)
    print(f"生成的标签：{{filename}}")


if __name__ == "__main__":
    example_usage()
'''

    return code


class LabelTemplateGeneratorSkill:
    """标签模板生成技能类"""

    def __init__(self):
        self.name = "label_template_generator"
        self.description = "从图片生成标签模板代码，支持基于参考图片创建 Python 标签生成器，自动识别固定标签和可变数据"

    def execute(
        self,
        image_path: str,
        class_name: str = "LabelTemplateGenerator",
        output_file: Optional[str] = None,
        enable_ocr: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        执行标签模板生成

        Args:
            image_path: 输入图片路径
            class_name: 生成的类名
            output_file: 输出 Python 文件路径（可选）
            enable_ocr: 是否启用 OCR 识别
            verbose: 是否生成详细代码

        Returns:
            生成结果
        """
        try:
            analysis = analyze_image(image_path, verbose=verbose)
            
            if not analysis["success"]:
                return analysis

            ocr_result = None
            if enable_ocr:
                ocr_result = extract_text_with_ocr(image_path)
                if ocr_result.get('success'):
                    logger.info(f"OCR 识别成功，提取 {len(ocr_result.get('fields', []))} 个字段")

            code = generate_template_code(image_path, class_name, ocr_result, verbose)

            result = {
                "success": True,
                "analysis": analysis,
                "ocr_result": ocr_result,
                "code": code
            }

            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(code)
                    result["output_file"] = output_file
                except Exception as e:
                    result["output_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"生成标签模板失败：{e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_skill_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "image_path": {"type": "string", "required": True, "description": "输入图片路径"},
                "class_name": {"type": "string", "required": False, "description": "生成的类名"},
                "output_file": {"type": "string", "required": False, "description": "输出 Python 文件路径"},
                "enable_ocr": {"type": "boolean", "required": False, "description": "是否启用 OCR 识别"},
                "verbose": {"type": "boolean", "required": False, "description": "是否生成详细代码"}
            }
        }


_skill_instance: Optional[LabelTemplateGeneratorSkill] = None


def get_label_template_generator_skill() -> LabelTemplateGeneratorSkill:
    """获取标签模板生成技能单例"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = LabelTemplateGeneratorSkill()
    return _skill_instance


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="标签模板生成器 - 从图片生成 Python 标签模板代码")
    parser.add_argument("-i", "--image", required=True, help="输入图片路径")
    parser.add_argument("-o", "--output", help="输出 Python 文件路径")
    parser.add_argument("-n", "--name", default="LabelTemplateGenerator", help="生成的类名")
    parser.add_argument("--no-ocr", action="store_true", help="禁用 OCR 识别")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出模式")

    args = parser.parse_args()

    skill = LabelTemplateGeneratorSkill()
    result = skill.execute(args.image, args.name, args.output, not args.no_ocr, args.verbose)

    if result["success"]:
        print(f"✓ 分析成功!")
        print(f"  图片：{result['analysis']['file']}")
        print(f"  尺寸：{result['analysis']['size']['width']} x {result['analysis']['size']['height']}")
        
        if result.get('ocr_result') and result['ocr_result'].get('success'):
            fields = result['ocr_result'].get('fields', [])
            print(f"  OCR 识别字段数：{len(fields)}")
            for field in fields[:10]:  # 显示前 10 个
                print(f"    - {field['label']}: {field['value']} (类型：{field['type']})")
        
        if "output_file" in result:
            print(f"  代码已保存到：{result['output_file']}")
        else:
            print("\n" + "=" * 60)
            print(result["code"][:2000] + "...")  # 只显示前 2000 字符
    else:
        print(f"✗ 失败：{result.get('error', '未知错误')}")
        sys.exit(1)
