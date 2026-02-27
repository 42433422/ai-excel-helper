#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将商标标签PNG图片转换为PDF文件
"""

import os
import glob
from PIL import Image
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def convert_png_to_pdf():
    """将商标导出目录中的PNG图片转换为PDF"""
    
    # 商标导出目录
    labels_dir = "商标导出"
    
    if not os.path.exists(labels_dir):
        logger.error(f"商标导出目录不存在: {labels_dir}")
        return False
    
    # 查找所有PNG文件
    png_files = glob.glob(os.path.join(labels_dir, "*.png"))
    
    if not png_files:
        logger.error("未找到PNG图片文件")
        return False
    
    # 按文件名排序
    png_files.sort()
    
    logger.info(f"找到 {len(png_files)} 个PNG文件:")
    for i, file in enumerate(png_files, 1):
        logger.info(f"  {i}. {os.path.basename(file)}")
    
    try:
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
            return False
        
        # 输出PDF文件路径
        output_pdf = "商标标签完整版.pdf"
        
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
                output_pdf = f"商标标签完整版_{timestamp}.pdf"
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
                logger.info(f"✅ PDF转换成功: {output_pdf}")
                logger.info(f"   总页数: {len(images)}")
                logger.info(f"   文件大小: {os.path.getsize(output_pdf) / 1024:.1f} KB")
                return True
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
                    logger.info(f"✅ PDF转换成功（使用临时文件）: {output_pdf}")
                    return True
                except Exception as temp_e:
                    logger.error(f"临时文件方案也失败: {temp_e}")
                    return False
        
    except Exception as e:
        logger.error(f"PDF转换失败: {e}")
        return False

if __name__ == "__main__":
    logger.info("开始将商标标签PNG转换为PDF...")
    
    # 设置工作目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    success = convert_png_to_pdf()
    
    if success:
        logger.info("转换完成!")
    else:
        logger.error("转换失败!")
