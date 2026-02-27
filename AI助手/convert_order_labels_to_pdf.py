#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将指定订单的标签PNG图片转换为PDF文件
"""

import os
import glob
import logging
from PIL import Image
from typing import List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def convert_order_labels_to_pdf(order_number: str, labels_dir: str = "商标导出") -> tuple:
    """
    将指定订单的标签转换为PDF
    
    Args:
        order_number: 订单号，如"26-0200053A"
        labels_dir: 标签目录路径
    
    Returns:
        tuple: (success, pdf_file_path) - 转换是否成功和实际生成的PDF文件路径
    """
    try:
        if not os.path.exists(labels_dir):
            logger.error(f"标签目录不存在: {labels_dir}")
            return False
        
        # 查找指定订单的所有标签PNG文件
        label_pattern = os.path.join(labels_dir, f"*{order_number}*.png")
        png_files = glob.glob(label_pattern)
        
        if not png_files:
            logger.warning(f"订单 {order_number} 没有找到标签文件: {label_pattern}")
            return False, None
        
        # 按文件名排序
        png_files.sort()
        
        logger.info(f"为订单 {order_number} 找到 {len(png_files)} 个标签文件:")
        for i, file in enumerate(png_files, 1):
            logger.info(f"  {i}. {os.path.basename(file)}")
        
        # 打开所有图片
        images = []
        for png_file in png_files:
            try:
                img = Image.open(png_file)
                # 转换为RGB模式（如果需要）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
                logger.info(f"已加载: {os.path.basename(png_file)} ({img.size[0]}x{img.size[1]})")
            except Exception as e:
                logger.error(f"无法加载图片 {png_file}: {e}")
                return False
        
        if not images:
            logger.error("没有成功加载任何图片")
            return False, None
        
        # 输出PDF文件路径（使用专门的PDF文件夹）
        output_dir = "PDF文件"
        output_pdf = os.path.join(output_dir, f"订单{order_number}_标签.pdf")
        
        # 确保PDF文件夹存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建PDF文件夹: {output_dir}")
        
        # 尝试删除已存在的PDF文件
        if os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
                logger.info(f"已删除已存在的PDF文件: {output_pdf}")
            except Exception as e:
                logger.warning(f"无法删除已存在的PDF文件: {e}")
                # 使用新的文件名
                import time
                timestamp = int(time.time())
                output_pdf = os.path.join(output_dir, f"订单{order_number}_标签_{timestamp}.pdf")
                logger.info(f"使用新的文件名: {output_pdf}")
        
        # 保存为PDF
        if images:
            # 第一张图片作为基础
            first_img = images[0]
            # 其他图片作为附加页
            other_images = images[1:] if len(images) > 1 else []
            
            try:
                first_img.save(
                    output_pdf,
                    "PDF",
                    save_all=True,
                    append_images=other_images,
                    quality=95,
                    optimize=True
                )
                logger.info(f"✅ 订单 {order_number} PDF转换成功: {output_pdf}")
                logger.info(f"   总页数: {len(images)}")
                logger.info(f"   文件大小: {os.path.getsize(output_pdf) / 1024:.1f} KB")
                return True, output_pdf
            except PermissionError:
                logger.error(f"权限错误，无法写入PDF文件: {output_pdf}")
                # 尝试使用临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_pdf_path = temp_file.name
                
                try:
                    first_img.save(
                        temp_pdf_path,
                        "PDF",
                        save_all=True,
                        append_images=other_images,
                        quality=95,
                        optimize=True
                    )
                    # 尝试移动到目标位置
                    import shutil
                    shutil.move(temp_pdf_path, output_pdf)
                    logger.info(f"✅ 订单 {order_number} PDF转换成功（使用临时文件）: {output_pdf}")
                    return True, output_pdf
                except Exception as temp_e:
                    logger.error(f"临时文件方案也失败: {temp_e}")
                    return False, None
        
        return True
        
    except Exception as e:
        logger.error(f"订单 {order_number} PDF转换失败: {e}")
        return False, None

def get_order_labels(order_number: str, labels_dir: str = "商标导出") -> List[str]:
    """
    获取指定订单的标签文件列表
    
    Args:
        order_number: 订单号
        labels_dir: 标签目录路径
    
    Returns:
        List[str]: 标签文件路径列表
    """
    try:
        if not os.path.exists(labels_dir):
            return []
        
        # 查找指定订单的所有标签PNG文件
        label_pattern = os.path.join(labels_dir, f"*{order_number}*.png")
        png_files = glob.glob(label_pattern)
        
        # 按文件名排序
        png_files.sort()
        
        return png_files
        
    except Exception as e:
        logger.error(f"获取订单 {order_number} 标签文件失败: {e}")
        return []

def convert_each_label_to_pdf(order_number: str, product_names: list = None, labels_dir: str = "商标导出") -> list:
    """
    将指定订单的每个标签PNG转换为单独的PDF文件
    
    Args:
        order_number: 订单号，如"26-0200053A"
        product_names: 产品名称列表，如 ["PE白底漆", "稀释剂1号"]
        labels_dir: 标签目录路径
    
    Returns:
        list: [(pdf_file_path, product_name), ...] - 每个产品的PDF文件路径和产品名称
    """
    try:
        # 创建标签目录（如果不存在）
        if not os.path.exists(labels_dir):
            os.makedirs(labels_dir)
            logger.info(f"创建标签目录: {labels_dir}")
        
        # 查找指定订单的所有标签PNG文件
        label_pattern = os.path.join(labels_dir, f"*{order_number}*.png")
        png_files = glob.glob(label_pattern)
        
        if not png_files:
            logger.warning(f"订单 {order_number} 没有找到标签文件: {label_pattern}")
            return []
        
        # 按文件名排序
        png_files.sort()
        
        logger.info(f"为订单 {order_number} 找到 {len(png_files)} 个标签文件:")
        for i, file in enumerate(png_files, 1):
            logger.info(f"  {i}. {os.path.basename(file)}")
        
        # 输出PDF文件目录
        output_dir = "PDF文件"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建PDF文件夹: {output_dir}")
        
        pdf_results = []
        
        # 为每个PNG文件单独生成PDF
        for i, png_file in enumerate(png_files):
            try:
                img = Image.open(png_file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 获取产品名称
                if product_names and i < len(product_names):
                    # 清理产品名称（去掉特殊字符）
                    clean_product_name = product_names[i].replace(" ", "_").replace("/", "_").replace("\\", "_")
                    # 限制长度
                    if len(clean_product_name) > 20:
                        clean_product_name = clean_product_name[:20]
                    product_name = clean_product_name
                else:
                    product_name = f"产品{i+1}"
                
                # 生成PDF文件名（包含产品名称）
                output_pdf = os.path.join(output_dir, f"{order_number}_{product_name}.pdf")
                
                # 尝试删除已存在的PDF文件
                if os.path.exists(output_pdf):
                    try:
                        os.remove(output_pdf)
                    except:
                        pass
                
                # 保存为PDF
                img.save(output_pdf, "PDF", quality=95, optimize=True)
                
                logger.info(f"✅ 生成PDF: {output_pdf}")
                pdf_results.append((output_pdf, product_name))
                
            except Exception as e:
                logger.error(f"生成PDF失败 {png_file}: {e}")
        
        if pdf_results:
            logger.info(f"✅ 成功生成 {len(pdf_results)} 个PDF文件")
        else:
            logger.error("❌ 没有成功生成任何PDF文件")
        
        return pdf_results
        
    except Exception as e:
        logger.error(f"转换失败: {e}")
        return []

if __name__ == "__main__":
    # 测试函数
    import sys
    
    if len(sys.argv) > 1:
        order_number = sys.argv[1]
        logger.info(f"开始转换订单 {order_number} 的标签为单独的PDF...")
        
        pdf_files = convert_each_label_to_pdf(order_number)
        
        if pdf_files:
            logger.info(f"转换完成! 生成了 {len(pdf_files)} 个PDF文件:")
            for pdf, name in pdf_files:
                logger.info(f"  - {pdf}")
        else:
            logger.error("转换失败!")
    else:
        logger.info("用法: python convert_order_labels_to_pdf.py <订单号>")
        logger.info("示例: python convert_order_labels_to_pdf.py 26-0200053A")
