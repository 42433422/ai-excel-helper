#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只打印单个标签的PDF打印机
"""

import os
import sys
import glob
import logging
from typing import List, Dict, Optional
from PIL import Image
from print_utils import print_document

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

class SingleLabelPrinter:
    """单标签PDF打印机"""
    
    def __init__(self):
        self.label_printer = None
        self.setup_printer()
    
    def setup_printer(self):
        """设置TSC TTP-244标签打印机"""
        try:
            from print_utils import get_printers
            printers = get_printers()
            
            # 查找TSC TTP-244打印机
            for printer in printers:
                if 'TSC TTP-244' in printer.get('name', '') or 'TTP-244' in printer.get('name', ''):
                    self.label_printer = printer
                    logger.info(f"找到标签打印机: {printer.get('name')}")
                    return
            
            # 如果没找到TSC TTP-244，使用第二个打印机
            if len(printers) >= 2:
                self.label_printer = printers[1]
                logger.info(f"未找到TSC TTP-244，使用第二个打印机: {self.label_printer.get('name')}")
            elif printers:
                self.label_printer = printers[0]
                logger.info(f"使用第一个打印机: {self.label_printer.get('name')}")
            else:
                logger.error("未找到可用的打印机")
                
        except Exception as e:
            logger.error(f"设置打印机失败: {e}")
    
    def create_single_label_pdf(self, png_files: List[str], label_index: int = 0) -> str:
        """创建只包含单个标签的PDF文件"""
        try:
            if not png_files or label_index >= len(png_files):
                logger.error(f"PNG文件列表为空或索引超出范围: {label_index}")
                return None
            
            # 只选择第一个标签
            selected_file = png_files[label_index]
            logger.info(f"选择标签文件: {os.path.basename(selected_file)}")
            
            # 打开图片并转换为RGB
            img = Image.open(selected_file)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 创建PDF文件
            output_pdf = f"单标签_{label_index + 1}.pdf"
            img.save(output_pdf, "PDF", quality=95, optimize=True)
            
            logger.info(f"创建单标签PDF成功: {output_pdf}")
            logger.info(f"标签尺寸: {img.size[0]}x{img.size[1]} 像素")
            
            return output_pdf
            
        except Exception as e:
            logger.error(f"创建单标签PDF失败: {e}")
            return None
    
    def print_single_label(self, label_index: int = 0, copies: int = 1) -> Dict:
        """打印单个标签"""
        try:
            if not self.label_printer:
                return {"success": False, "message": "未找到可用的标签打印机"}
            
            # 查找PNG文件
            labels_dir = "商标导出"
            if not os.path.exists(labels_dir):
                return {"success": False, "message": f"标签目录不存在: {labels_dir}"}
            
            png_files = glob.glob(os.path.join(labels_dir, "*.png"))
            if not png_files:
                return {"success": False, "message": "未找到PNG标签文件"}
            
            # 按文件名排序
            png_files.sort()
            
            # 创建单个标签PDF
            pdf_file = self.create_single_label_pdf(png_files, label_index)
            if not pdf_file:
                return {"success": False, "message": "创建单标签PDF失败"}
            
            logger.info(f"开始打印单个标签: {os.path.basename(pdf_file)}")
            logger.info(f"打印机: {self.label_printer.get('name')}")
            logger.info(f"份数: {copies}")
            
            # 执行打印
            all_success = True
            for i in range(copies):
                result = print_document(pdf_file, self.label_printer.get('name'))
                if not result.get('success', False):
                    logger.warning(f"第 {i+1} 份打印失败: {result.get('message', 'Unknown error')}")
                    all_success = False
                else:
                    logger.info(f"第 {i+1} 份打印成功")
            
            if all_success:
                logger.info("✅ 单标签打印成功")
                return {
                    "success": True, 
                    "message": f"单标签打印成功", 
                    "file": pdf_file, 
                    "label_index": label_index + 1,
                    "copies": copies
                }
            else:
                logger.error("❌ 部分单标签打印失败")
                return {"success": False, "message": "部分单标签打印失败"}
                
        except Exception as e:
            logger.error(f"单标签打印异常: {e}")
            return {"success": False, "message": f"单标签打印异常: {str(e)}"}

def print_single_label(label_index: int = 0, copies: int = 1) -> Dict:
    """打印单个标签的主函数"""
    printer = SingleLabelPrinter()
    return printer.print_single_label(label_index, copies)

if __name__ == "__main__":
    # 测试单标签打印功能
    print("开始测试单标签打印...")
    
    result = print_single_label(label_index=0, copies=1)
    print(f"打印结果: {result}")
