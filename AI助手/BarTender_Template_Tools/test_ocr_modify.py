#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OCR文字修改功能
"""

import os
import sys
import logging
from automate_bartender_gui import BarTenderGUIAutomator

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_ocr_modify.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_ocr_modify():
    """
    测试OCR文字修改功能
    """
    # 创建自动化实例
    automator = BarTenderGUIAutomator()
    
    # 设置BarTender路径
    bartender_path = r'C:\Program Files\Seagull\BarTender Suite\bartend.exe'
    if not automator.set_bartender_path(bartender_path):
        logger.error("无法找到BarTender可执行文件，请手动指定正确路径")
        return False
    
    # 启动BarTender
    logger.info("正在启动BarTender...")
    if not automator.start_bartender():
        logger.error("启动BarTender失败")
        return False
    
    # 等待应用程序完全启动
    import time
    time.sleep(5)
    
    # 打开测试文件
    test_file = r'c:\Users\97088\Desktop\新建文件夹 (4)\1870B封固底.btw'
    if not os.path.exists(test_file):
        logger.error(f"测试文件不存在: {test_file}")
        return False
    
    logger.info(f"正在打开测试文件: {test_file}")
    if not automator.open_file(test_file):
        logger.error("打开测试文件失败")
        return False
    
    # 等待文件完全打开
    time.sleep(5)
    
    # 使用OCR识别并修改文字
    logger.info("正在测试OCR文字修改功能...")
    success = automator.ocr_modify_text("3712", "371一")
    
    if success:
        logger.info("OCR文字修改测试成功！")
    else:
        logger.error("OCR文字修改测试失败！")
    
    # 不保存文件，直接关闭
    logger.info("测试完成，关闭BarTender（不保存更改）...")
    # 发送Alt+F4关闭窗口
    import pyautogui
    pyautogui.hotkey('alt', 'f4')
    time.sleep(2)
    
    # 如果弹出保存对话框，选择"不保存"
    pyautogui.press('n')  # 假设"不保存"是n键
    time.sleep(2)
    
    return success

if __name__ == "__main__":
    logger.info("开始OCR文字修改测试")
    success = test_ocr_modify()
    logger.info(f"OCR文字修改测试{'成功' if success else '失败'}")
    sys.exit(0 if success else 1)
