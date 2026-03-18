#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF标签打印机
支持将PDF文件打印到TSC TTP-244标签打印机
"""

import os
import sys
import logging
from typing import Dict
from print_utils import print_document

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

class PDFLabelPrinter:
    """PDF标签打印机类"""
    
    def __init__(self):
        self.label_printer = None
        self.setup_printer()
    
    def setup_printer(self):
        """设置标签打印机"""
        try:
            # 使用动态获取标签打印机的方法
            from app_api import get_label_printer
            label_printer_name = get_label_printer()
            
            if label_printer_name:
                self.label_printer = {"name": label_printer_name}
                logger.info(f"找到标签打印机: {label_printer_name}")
            else:
                # 如果动态获取失败，使用原来的方法
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
    
    def print_pdf(self, pdf_path: str, show_app: bool = True, copies: int = 1) -> Dict:
        """
        打印PDF文件
        
        Args:
            pdf_path: PDF文件路径
            show_app: 是否显示PDF应用窗口
            copies: 打印份数
            
        Returns:
            dict: 打印结果
        """
        try:
            if not os.path.exists(pdf_path):
                return {"success": False, "message": f"PDF文件不存在: {pdf_path}"}
            
            if not self.label_printer:
                return {"success": False, "message": "未找到可用的标签打印机"}
            
            logger.info(f"开始打印PDF: {pdf_path}")
            logger.info(f"标签打印机: {self.label_printer.get('name')}")
            logger.info(f"显示PDF应用: {show_app}")
            logger.info(f"打印份数: {copies}")
            
            # 重要：明确指定标签打印机，不使用系统默认
            printer_name = self.label_printer.get('name')
            logger.info(f"明确指定标签打印机: {printer_name}")
            
            # 使用专门的PDF打印方法（支持show_app参数）
            from special_trademark_print import print_trademark_pdf
            
            # 执行多次打印
            success_count = 0
            for i in range(copies):
                logger.info(f"执行第 {i+1} 次打印")
                result = print_trademark_pdf(pdf_path, printer_name, show_app=show_app)
                if result.get('success'):
                    success_count += 1
                else:
                    logger.error(f"第 {i+1} 次打印失败: {result.get('message')}")
            
            if success_count == copies:
                logger.info(f"✅ PDF标签打印成功，共打印 {copies} 份")
                return {"success": True, "message": f"PDF标签打印成功，共打印 {copies} 份", "file": pdf_path, "show_app": show_app, "copies": copies}
            else:
                logger.error(f"❌ PDF标签打印部分失败，成功 {success_count} 份，失败 {copies - success_count} 份")
                return {"success": False, "message": f"PDF标签打印部分失败，成功 {success_count} 份，失败 {copies - success_count} 份"}
                
        except Exception as e:
            logger.error(f"PDF打印异常: {e}")
            return {"success": False, "message": f"PDF打印异常: {str(e)}"}

def print_pdf_labels(pdf_path: str, copies: int = 1, show_app: bool = True) -> Dict:
    """
    打印PDF标签的主函数
    
    Args:
        pdf_path: PDF文件路径
        copies: 打印份数
        show_app: 是否显示PDF应用窗口（默认True）
        
    Returns:
        dict: 打印结果
    """
    printer = PDFLabelPrinter()
    return printer.print_pdf(pdf_path, show_app=show_app, copies=copies)

if __name__ == "__main__":
    # 测试PDF打印功能
    # 优先测试PDF文件夹中的文件
    test_files = [
        "PDF文件/商标标签完整版.pdf",
        "PDF文件/订单26-0200099A_标签.pdf",
        "商标标签完整版.pdf"  # 备用：根目录
    ]
    
    pdf_path = None
    for test_file in test_files:
        if os.path.exists(test_file):
            pdf_path = test_file
            break
    
    if pdf_path:
        print(f"找到测试PDF文件: {pdf_path}")
        result = print_pdf_labels(pdf_path)
        print(f"打印结果: {result}")
    else:
        print("未找到任何PDF文件进行测试")
        print("可用的PDF文件:")
        if os.path.exists("PDF文件"):
            for file in os.listdir("PDF文件"):
                if file.endswith('.pdf'):
                    print(f"  - PDF文件/{file}")
