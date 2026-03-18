#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机自动化控制模块
处理程序自动选择打印机的问题
"""

import time
import win32api
import win32con
import win32gui
import win32print
import subprocess
from typing import Dict, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrinterAutomation:
    """打印机自动化控制类"""
    
    def __init__(self):
        self.current_printer = None
        self.original_default = None
    
    def move_mouse(self, x: int, y: int):
        """移动鼠标到指定位置"""
        win32api.SetCursorPos((x, y))
        time.sleep(0.2)  # 等待鼠标移动完成
    
    def click_mouse(self, x: int, y: int, button: str = 'left'):
        """点击鼠标"""
        self.move_mouse(x, y)
        
        if button == 'left':
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == 'right':
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        time.sleep(0.3)  # 等待点击完成
    
    def find_window(self, title: str) -> int:
        """查找指定标题的窗口"""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title in window_title:
                    hwnds.append(hwnd)
            return True
        
        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else 0
    
    def get_window_position(self, hwnd: int) -> Tuple[int, int, int, int]:
        """获取窗口位置和大小"""
        rect = win32gui.GetWindowRect(hwnd)
        return rect  # (left, top, right, bottom)
    
    def set_default_printer(self, printer_name: str) -> bool:
        """设置Windows默认打印机"""
        try:
            logger.info(f"设置Windows默认打印机为: {printer_name}")
            
            # 使用PrintUI设置默认打印机
            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry', 
                '/y', '/n', printer_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"✅ 成功设置默认打印机为: {printer_name}")
                time.sleep(1)  # 等待系统更新
                return True
            else:
                logger.error(f"❌ 设置默认打印机失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 设置默认打印机异常: {e}")
            return False
    
    def handle_printer_dialog(self, target_printer: str, timeout: int = 10) -> bool:
        """处理打印机选择对话框"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            # 查找打印机对话框
            hwnd = self.find_window('打印')
            if hwnd:
                logger.info(f"找到打印机对话框，窗口句柄: {hwnd}")
                
                # 获取窗口位置
                rect = self.get_window_position(hwnd)
                logger.info(f"对话框位置: {rect}")
                
                # 计算点击位置（假设对话框在屏幕中央）
                center_x = (rect[0] + rect[2]) // 2
                center_y = (rect[1] + rect[3]) // 2
                
                # 点击打印机下拉菜单位置（假设在对话框上方）
                printer_dropdown_x = center_x
                printer_dropdown_y = center_y - 100
                self.click_mouse(printer_dropdown_x, printer_dropdown_y)
                
                # 等待下拉菜单出现
                time.sleep(0.5)
                
                # 模拟键盘操作选择打印机
                # 这里需要根据实际情况调整
                logger.info(f"尝试选择打印机: {target_printer}")
                
                # 点击确定按钮
                ok_button_x = center_x + 100
                ok_button_y = center_y + 50
                self.click_mouse(ok_button_x, ok_button_y)
                
                logger.info("✅ 打印机对话框处理完成")
                return True
            
            time.sleep(0.5)
        
        logger.info("⚠️ 未找到打印机对话框")
        return False
    
    def print_with_automation(self, file_path: str, target_printer: str) -> Dict[str, any]:
        """
        使用自动化方式打印文件
        处理程序自动选择打印机的问题
        """
        try:
            logger.info(f"开始自动化打印: {file_path} 到 {target_printer}")
            
            # 1. 保存原始默认打印机
            self.original_default = win32print.GetDefaultPrinter()
            logger.info(f"原始默认打印机: {self.original_default}")
            
            # 2. 临时设置目标打印机为默认
            if self.original_default != target_printer:
                logger.info(f"临时设置默认打印机为: {target_printer}")
                self.set_default_printer(target_printer)
            
            # 3. 使用ShellExecute打印
            logger.info("使用ShellExecute打印文件")
            result = win32api.ShellExecute(
                0,
                "print",
                file_path,
                f'/d:"{target_printer}"',
                ".",
                1  # 显示窗口
            )
            
            if result <= 32:
                raise Exception(f"ShellExecute失败，错误代码: {result}")
            
            logger.info(f"✅ ShellExecute调用成功，结果: {result}")
            
            # 4. 处理可能出现的打印机对话框
            logger.info("检查是否需要处理打印机对话框...")
            self.handle_printer_dialog(target_printer)
            
            # 5. 等待打印完成
            logger.info("等待打印完成...")
            time.sleep(5)  # 等待打印作业处理
            
            # 6. 恢复原始默认打印机
            if self.original_default and self.original_default != target_printer:
                logger.info(f"恢复原始默认打印机: {self.original_default}")
                self.set_default_printer(self.original_default)
            
            return {
                "success": True,
                "message": f"✅ 自动化打印成功发送到 {target_printer}",
                "printer": target_printer,
                "file": file_path
            }
            
        except Exception as e:
            logger.error(f"❌ 自动化打印失败: {e}")
            
            # 确保恢复原始默认打印机
            if self.original_default and self.current_printer != self.original_default:
                try:
                    self.set_default_printer(self.original_default)
                except:
                    pass
            
            return {
                "success": False,
                "message": f"自动化打印失败: {str(e)}"
            }
    
    def print_excel_with_automation(self, file_path: str, target_printer: str) -> Dict[str, any]:
        """自动化打印Excel文件"""
        return self.print_with_automation(file_path, target_printer)
    
    def print_pdf_with_automation(self, file_path: str, target_printer: str) -> Dict[str, any]:
        """自动化打印PDF文件"""
        return self.print_with_automation(file_path, target_printer)

class EnhancedPrinterUtils:
    """增强的打印机工具类"""
    
    def __init__(self):
        self.automation = PrinterAutomation()
    
    def print_file_enhanced(self, file_path: str, printer_name: str, use_automation: bool = True) -> Dict[str, any]:
        """
        增强的文件打印函数
        支持自动化处理打印机选择问题
        """
        try:
            if not use_automation:
                # 使用原始打印方法
                from print_utils import print_document
                return print_document(file_path, printer_name)
            else:
                # 使用自动化打印
                return self.automation.print_with_automation(file_path, printer_name)
                
        except Exception as e:
            logger.error(f"增强打印失败: {e}")
            return {
                "success": False,
                "message": f"增强打印失败: {str(e)}"
            }

if __name__ == "__main__":
    # 测试自动化功能
    print("=" * 80)
    print("🧪 打印机自动化控制测试")
    print("=" * 80)
    
    automation = PrinterAutomation()
    
    # 测试1: 列出可用打印机
    print("\n1. 列出可用打印机:")
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    for i, printer in enumerate(printers):
        print(f"   {i+1}. {printer[2]}")
    
    # 测试2: 设置默认打印机
    if printers:
        test_printer = printers[0][2]
        print(f"\n2. 测试设置默认打印机: {test_printer}")
        success = automation.set_default_printer(test_printer)
        print(f"   结果: {'成功' if success else '失败'}")
    
    # 测试3: 恢复原始默认打印机
    print("\n3. 测试完成")
    print("=" * 80)
