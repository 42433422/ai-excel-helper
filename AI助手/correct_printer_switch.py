#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确的打印机切换实现
解决ShellExecute的/d参数对PDF应用无效的问题
"""

import os
import sys
import time
import win32api
import win32print
import subprocess
import logging
from typing import Dict, Tuple, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CorrectPrinterSwitcher:
    """正确的打印机切换器"""
    
    def __init__(self):
        self.original_printer = None
    
    def switch_printer(self, target_printer: str) -> Tuple[bool, str]:
        """
        临时切换默认打印机
        
        Args:
            target_printer: 目标打印机名称
            
        Returns:
            tuple: (是否成功, 原始打印机名称)
        """
        try:
            # 1. 保存原始默认打印机
            self.original_printer = win32print.GetDefaultPrinter()
            logger.info(f"原始默认打印机: {self.original_printer}")
            
            # 2. 如果目标打印机与当前相同，无需切换
            if self.original_printer == target_printer:
                logger.info(f"目标打印机与当前默认相同，无需切换: {target_printer}")
                return True, self.original_printer
            
            # 3. 使用rundll32命令切换默认打印机
            logger.info(f"切换默认打印机到: {target_printer}")
            
            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', target_printer
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"切换打印机失败: {result.stderr}")
                return False, self.original_printer
            
            # 4. 等待系统更新
            time.sleep(1)
            
            # 5. 验证切换结果
            new_default = win32print.GetDefaultPrinter()
            if new_default != target_printer:
                logger.error(f"切换验证失败: 期望 {target_printer}, 实际 {new_default}")
                return False, self.original_printer
            
            logger.info(f"✅ 成功切换默认打印机: {self.original_printer} -> {target_printer}")
            return True, self.original_printer
            
        except Exception as e:
            logger.error(f"切换打印机异常: {e}")
            return False, self.original_printer
    
    def restore_printer(self) -> bool:
        """
        恢复原始默认打印机
        
        Returns:
            bool: 是否成功恢复
        """
        try:
            if not self.original_printer:
                logger.warning("没有原始打印机记录，无需恢复")
                return True
            
            logger.info(f"恢复原始默认打印机: {self.original_printer}")
            
            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', self.original_printer
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"恢复打印机失败: {result.stderr}")
                return False
            
            # 等待系统更新
            time.sleep(1)
            
            # 验证恢复结果
            restored = win32print.GetDefaultPrinter()
            if restored != self.original_printer:
                logger.error(f"恢复验证失败: 期望 {self.original_printer}, 实际 {restored}")
                return False
            
            logger.info(f"✅ 成功恢复默认打印机: {restored}")
            return True
            
        except Exception as e:
            logger.error(f"恢复打印机异常: {e}")
            return False
    
    def print_file(self, file_path: str, target_printer: str) -> Dict[str, any]:
        """
        使用正确的打印机切换打印文件
        
        Args:
            file_path: 文件路径
            target_printer: 目标打印机名称
            
        Returns:
            Dict: 打印结果
        """
        try:
            # 1. 验证文件存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}"
                }
            
            logger.info(f"准备打印文件: {file_path}")
            logger.info(f"目标打印机: {target_printer}")
            
            # 2. 切换到目标打印机
            success, original = self.switch_printer(target_printer)
            
            if not success:
                return {
                    "success": False,
                    "message": f"切换到打印机 {target_printer} 失败"
                }
            
            # 3. 执行打印（不使用/d参数，直接使用默认打印机）
            logger.info(f"执行打印到当前默认打印机...")
            
            result = win32api.ShellExecute(
                0,
                "print",
                file_path,
                "",  # 不使用/d参数，直接使用系统默认打印机
                ".",
                0  # SW_HIDE
            )
            
            if result <= 32:
                logger.error(f"ShellExecute失败，错误代码: {result}")
                self.restore_printer()
                return {
                    "success": False,
                    "message": f"打印失败，错误代码: {result}"
                }
            
            logger.info(f"✅ 打印命令已发送，ShellExecute结果: {result}")
            
            # 4. 等待打印完成
            logger.info("等待打印任务处理...")
            time.sleep(3)
            
            # 5. 恢复原始默认打印机
            self.restore_printer()
            
            return {
                "success": True,
                "message": f"✅ 成功打印到 {target_printer}",
                "file": file_path,
                "printer": target_printer,
                "shell_result": result
            }
            
        except Exception as e:
            logger.error(f"打印失败: {e}")
            # 确保恢复打印机
            self.restore_printer()
            return {
                "success": False,
                "message": f"打印异常: {str(e)}"
            }
    
    def print_pdf(self, pdf_path: str, target_printer: str) -> Dict[str, any]:
        """
        打印PDF文件到指定打印机
        
        Args:
            pdf_path: PDF文件路径
            target_printer: 目标打印机名称
            
        Returns:
            Dict: 打印结果
        """
        return self.print_file(pdf_path, target_printer)
    
    def print_excel(self, excel_path: str, target_printer: str) -> Dict[str, any]:
        """
        打印Excel文件到指定打印机
        
        Args:
            excel_path: Excel文件路径
            target_printer: 目标打印机名称
            
        Returns:
            Dict: 打印结果
        """
        return self.print_file(excel_path, target_printer)

# 便捷函数
def print_to_printer(file_path: str, printer_name: str) -> Dict[str, any]:
    """
    打印文件到指定打印机（自动切换默认打印机）
    
    Args:
        file_path: 文件路径
        printer_name: 打印机名称
        
    Returns:
        Dict: 打印结果
    """
    switcher = CorrectPrinterSwitcher()
    return switcher.print_file(file_path, printer_name)

def print_pdf_to_label_printer(pdf_path: str) -> Dict[str, any]:
    """
    打印PDF到标签打印机（自动切换默认打印机）
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        Dict: 打印结果
    """
    label_printer = "TSC TTP-244 Plus"
    switcher = CorrectPrinterSwitcher()
    return switcher.print_pdf(pdf_path, label_printer)

def print_doc_to_document_printer(doc_path: str) -> Dict[str, any]:
    """
    打印文档到发货单打印机（自动切换默认打印机）
    
    Args:
        doc_path: 文档文件路径
        
    Returns:
        Dict: 打印结果
    """
    doc_printer = "Jolimark 24-pin printer"
    switcher = CorrectPrinterSwitcher()
    return switcher.print_file(doc_path, doc_printer)

# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 正确打印机切换实现测试")
    print("=" * 80)
    
    # 测试切换功能
    print("\n📋 测试打印机切换")
    
    # 获取当前默认打印机
    current = win32print.GetDefaultPrinter()
    print(f"当前默认打印机: {current}")
    
    # 创建切换器
    switcher = CorrectPrinterSwitcher()
    
    # 测试切换到TSC
    print(f"\n测试切换到 TSC TTP-244 Plus...")
    success, original = switcher.switch_printer("TSC TTP-244 Plus")
    
    if success:
        print(f"✅ 切换成功")
        
        # 恢复
        print(f"\n恢复原始打印机...")
        if switcher.restore_printer():
            print(f"✅ 恢复成功")
    else:
        print(f"❌ 切换失败")
    
    # 测试实际打印（如果有测试文件）
    print("\n📋 测试实际打印")
    
    test_files = [
        "PDF文件/订单26-0200123A_标签.pdf",
        "outputs/发货单_测试.xlsx"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n测试打印: {test_file}")
            
            if test_file.endswith('.pdf'):
                printer = "TSC TTP-244 Plus" if "标签" in test_file else "Jolimark 24-pin printer"
            else:
                printer = "Jolimark 24-pin printer"
            
            print(f"使用打印机: {printer}")
            
            result = print_to_printer(test_file, printer)
            print(f"结果: {result.get('message', '未知')}")
    
    print("\n" + "=" * 80)
    print("🎉 测试完成")
    print("=" * 80)
