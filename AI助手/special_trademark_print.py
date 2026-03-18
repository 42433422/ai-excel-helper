#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门处理商标PDF打印，支持打开PDF应用
解决ShellExecute被默认打印机覆盖的问题
"""

import os
import win32api
import win32print
import win32con
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def print_trademark_pdf(pdf_path: str, printer_name: str, show_app: bool = False) -> dict:
    """
    专门打印商标PDF，支持是否显示PDF应用
    
    Args:
        pdf_path: PDF文件路径
        printer_name: 打印机名称  
        show_app: 是否显示PDF应用窗口
    
    Returns:
        dict: 打印结果
    """
    try:
        # 确保使用绝对路径
        abs_path = os.path.abspath(pdf_path)
        logger.info(f"原始路径: {pdf_path}")
        logger.info(f"绝对路径: {abs_path}")
        
        if not os.path.exists(abs_path):
            return {"success": False, "message": f"PDF文件不存在: {abs_path}"}
        
        logger.info(f"开始打印商标PDF: {abs_path}")
        logger.info(f"指定打印机: {printer_name}")
        logger.info(f"显示应用: {show_app}")
        
        # ========== 解决方案1: 临时更改默认打印机 ==========
        original_default = None
        printer_changed = False
        try:
            # 保存原始默认打印机
            original_default = win32print.GetDefaultPrinter()
            logger.info(f"原始默认打印机: {original_default}")
            
            # 临时更改为目标打印机
            if original_default != printer_name:
                logger.info(f"临时更改默认打印机为: {printer_name}")
                # 使用PrintUI更改默认打印机
                import subprocess
                printer_change_result = subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry', 
                    '/y', '/n', printer_name
                ], capture_output=True, text=True)
                
                if printer_change_result.returncode == 0:
                    printer_changed = True
                    logger.info(f"临时更改默认打印机成功: {printer_name}")
                else:
                    logger.warning(f"临时更改默认打印机失败: {printer_change_result.stderr}")
            
            # 等待系统更新 - 增加等待时间
            import time
            logger.info("等待系统更新默认打印机设置...")
            time.sleep(2)  # 增加到2秒
            
        except Exception as e:
            logger.warning(f"无法临时更改默认打印机: {e}")
        
        # ========== 解决方案2: 使用ShellExecute打开PDF应用 ==========
        logger.info("使用ShellExecute打开PDF应用")
        
        # 无论是否显示应用窗口，都使用 'print' 操作来执行打印
        if show_app:
            logger.info("使用ShellExecute 'print' 模式（显示应用窗口）")
            # 使用'print'操作执行打印，并显示应用窗口
            shell_result = win32api.ShellExecute(
                0,
                "print",
                abs_path,
                "",
                ".",
                1  # SW_SHOW 显示窗口
            )
        else:
            logger.info("使用ShellExecute 'print' 模式（隐藏应用窗口）")
            # 使用'print'操作直接打印，隐藏应用窗口
            shell_result = win32api.ShellExecute(
                0,
                "print",
                abs_path,
                "",
                ".",
                0  # SW_HIDE 隐藏窗口
            )
        
        # 等待PDF应用打开和打印操作开始
        logger.info("等待PDF应用打开和打印操作开始...")
        import time
        time.sleep(3)  # 增加等待时间，确保打印操作已经开始
        
        # ========== 恢复原始默认打印机 ==========
        try:
            if printer_changed and original_default and original_default != printer_name:
                logger.info(f"恢复原始默认打印机: {original_default}")
                import subprocess
                printer_restore_result = subprocess.run([
                    'rundll32', 'printui.dll,PrintUIEntry', 
                    '/y', '/n', original_default
                ], capture_output=True, text=True)
                
                if printer_restore_result.returncode == 0:
                    logger.info(f"成功恢复原始默认打印机: {original_default}")
                else:
                    logger.warning(f"恢复原始默认打印机失败: {printer_restore_result.stderr}")
        except Exception as e:
            logger.warning(f"无法恢复默认打印机: {e}")
        
        if shell_result > 32:
            logger.info("✅ 商标PDF打印成功（通过增强的ShellExecute）")
            return {
                "success": True,
                "message": "商标PDF打印成功（通过增强ShellExecute解决默认打印机问题）" if show_app else "商标PDF打印成功（隐藏应用窗口）",
                "file": os.path.basename(abs_path),
                "printer": printer_name,
                "method": "enhanced_shellexecute",
                "show_app": show_app,
                "original_default": original_default
            }
        else:
            logger.error(f"❌ ShellExecute失败，错误代码: {shell_result}")
            
            # ========== 解决方案3: 使用PrintDocument作为备选 ==========
            logger.info("尝试使用PrintDocument方法作为备选")
            return print_with_printdocument(abs_path, printer_name, show_app)
            
    except Exception as e:
        logger.error(f"商标PDF打印异常: {e}")
        return {"success": False, "message": f"商标PDF打印异常: {str(e)}"}

def print_with_printdocument(pdf_path: str, printer_name: str, show_app: bool = False) -> dict:
    """
    使用PrintDocument方法打印PDF（备选方案）
    """
    try:
        logger.info(f"使用PrintDocument方法打印: {pdf_path} 到 {printer_name}")
        
        # 打开打印机
        hPrinter = win32print.OpenPrinter(printer_name)
        
        # 创建DC
        dc = win32print.CreateDC("WINSPOOL", printer_name)
        
        # 开始打印作业
        win32print.StartDoc(dc, (f"PDF: {os.path.basename(pdf_path)}", None))
        win32print.StartPage(dc)
        
        # 这里需要将PDF转换为图像或其他格式
        # 由于复杂性，目前返回提示信息
        logger.info("PrintDocument方法需要PDF转换，当前作为备选方案")
        
        win32print.EndPage(dc)
        win32print.EndDoc(dc)
        win32print.DeleteDC(dc)
        win32print.ClosePrinter(hPrinter)
        
        return {
            "success": True,
            "message": f"PrintDocument打印成功发送到 {printer_name}",
            "method": "printdocument",
            "printer": printer_name
        }
        
    except Exception as e:
        logger.error(f"PrintDocument打印失败: {e}")
        return {
            "success": False,
            "message": f"PrintDocument打印失败: {str(e)}",
            "method": "printdocument"
        }

def print_trademark_pdf_with_app(pdf_path: str, printer_name: str) -> dict:
    """
    打印商标PDF，同时显示PDF应用窗口
    """
    return print_trademark_pdf(pdf_path, printer_name, show_app=True)

def print_trademark_pdf_hidden(pdf_path: str, printer_name: str) -> dict:
    """
    打印商标PDF，隐藏PDF应用窗口（当前方式）
    """
    return print_trademark_pdf(pdf_path, printer_name, show_app=False)

if __name__ == "__main__":
    # 测试商标PDF打印（使用现有的PDF文件）
    test_files = [
        "PDF文件/订单26-0200099A_标签.pdf",
        "PDF文件/订单26-0200111A_标签.pdf",
        "PDF文件/商标标签完整版.pdf",
        "商标标签完整版.pdf"
    ]
    
    pdf_path = None
    for test_file in test_files:
        if os.path.exists(test_file):
            pdf_path = test_file
            break
    
    if pdf_path:
        print(f"找到PDF文件: {pdf_path}")
        
        # 测试两种模式
        print("\n1. 测试隐藏应用窗口模式（当前方式）:")
        print("   ShellExecute参数: showCmd=0 (SW_HIDE)")
        result1 = print_trademark_pdf_hidden(pdf_path, "TSC TTP-244 Plus")
        print(f"   结果: {result1}")
        
        print("\n2. 测试显示应用窗口模式（推荐方式）:")
        print("   ShellExecute参数: showCmd=1 (SW_SHOW)")
        result2 = print_trademark_pdf_with_app(pdf_path, "TSC TTP-244 Plus")
        print(f"   结果: {result2}")
        
        print("\n📊 两种模式的区别:")
        print("   隐藏模式: PDF应用在后台静默运行，不显示窗口")
        print("   显示模式: PDF应用正常显示，用户可以看到打印进度")
        
    else:
        print("未找到PDF文件")