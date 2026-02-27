#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门测试TSC TTP-244 Plus打印机
"""

import os
import sys
import win32print
import win32api
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def find_tsc_printer():
    """
    专门查找TSC TTP-244 Plus打印机
    """
    try:
        # 获取所有打印机
        printers = []
        all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        logger.info(f"找到 {len(all_printers)} 个打印机")
        
        for printer_info in all_printers:
            if isinstance(printer_info, tuple) and len(printer_info) >= 2:
                printer_name = printer_info[2] if len(printer_info) > 2 else printer_info[1]
                printers.append(printer_name)
                logger.info(f"  打印机: {printer_name}")
        
        # 专门查找TSC TTP-244
        tsc_printer = None
        for printer in printers:
            if 'TSC TTP-244' in printer or 'TTP-244' in printer:
                tsc_printer = printer
                logger.info(f"✅ 找到TSC TTP-244打印机: {tsc_printer}")
                break
        
        if not tsc_printer:
            logger.warning("❌ 未找到TSC TTP-244打印机")
            logger.info("可用打印机列表:")
            for i, printer in enumerate(printers, 1):
                logger.info(f"  {i}. {printer}")
        
        return tsc_printer
        
    except Exception as e:
        logger.error(f"查找打印机失败: {e}")
        return None

def test_tsc_printer(printer_name):
    """
    测试TSC打印机是否可用
    """
    try:
        # 尝试打开打印机
        hprinter = win32print.OpenPrinter(printer_name)
        logger.info(f"✅ 成功打开TSC打印机: {printer_name}")
        
        # 获取打印机状态
        printer_info = win32print.GetPrinter(hprinter, 2)
        status = printer_info.get('Status', 0)
        status_text = "就绪" if status == 0 else f"状态码: {status}"
        logger.info(f"打印机状态: {status_text}")
        
        win32print.ClosePrinter(hprinter)
        return True
        
    except Exception as e:
        logger.error(f"测试TSC打印机失败: {e}")
        return False

def print_test_to_tsc(printer_name, test_file):
    """
    打印测试文件到TSC打印机
    """
    try:
        if not os.path.exists(test_file):
            logger.error(f"测试文件不存在: {test_file}")
            return False
        
        logger.info(f"尝试打印到TSC打印机: {printer_name}")
        
        # 使用ShellExecute直接打印到指定打印机
        result = win32api.ShellExecute(
            0,
            "print",
            test_file,
            f'/d:"{printer_name}"',
            ".",
            0
        )
        
        if result > 32:
            logger.info(f"✅ 测试文件已发送到TSC打印机: {test_file}")
            return True
        else:
            logger.error(f"❌ ShellExecute失败，错误代码: {result}")
            return False
            
    except Exception as e:
        logger.error(f"打印到TSC打印机失败: {e}")
        return False

def create_test_pdf():
    """
    创建测试PDF文件
    """
    try:
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, txt="TSC打印机测试", ln=True, align="C")
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="这是一个测试页面", ln=True, align="C")
        pdf.cell(200, 10, txt="如果您看到此页面，说明TSC打印机工作正常", ln=True, align="C")
        
        output_path = "tsc_test.pdf"
        pdf.output(output_path)
        logger.info(f"✅ 创建测试PDF: {output_path}")
        return output_path
        
    except ImportError:
        logger.warning("未安装fpdf，使用现有PDF文件")
        return "商标标签完整版.pdf"
    except Exception as e:
        logger.error(f"创建测试PDF失败: {e}")
        return "商标标签完整版.pdf"

def main():
    """
    主函数
    """
    logger.info("=== TSC TTP-244 Plus 打印机测试 ===")
    
    # 1. 查找TSC打印机
    tsc_printer = find_tsc_printer()
    
    if not tsc_printer:
        logger.error("❌ 无法继续，未找到TSC打印机")
        return
    
    # 2. 测试打印机连接
    logger.info("\n=== 测试打印机连接 ===")
    connected = test_tsc_printer(tsc_printer)
    
    if not connected:
        logger.error("❌ 打印机连接测试失败")
        return
    
    # 3. 创建测试文件
    logger.info("\n=== 创建测试文件 ===")
    test_file = create_test_pdf()
    
    # 4. 打印测试
    logger.info("\n=== 测试打印 ===")
    print_success = print_test_to_tsc(tsc_printer, test_file)
    
    if print_success:
        logger.info("✅ TSC打印机测试成功！")
        logger.info(f"   打印机: {tsc_printer}")
        logger.info(f"   测试文件: {test_file}")
    else:
        logger.error("❌ TSC打印机测试失败！")
    
    logger.info("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
