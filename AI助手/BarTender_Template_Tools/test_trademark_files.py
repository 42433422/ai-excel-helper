#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试商标集锦目录下的所有BTW文件
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
        logging.FileHandler('test_trademark_files.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_trademark_files():
    """
    测试商标集锦目录下的所有BTW文件
    """
    # 创建自动化实例
    automator = BarTenderGUIAutomator()
    
    # 设置BarTender路径
    bartender_path = r'C:\Program Files\Seagull\BarTender Suite\bartend.exe'
    if not automator.set_bartender_path(bartender_path):
        logger.error("无法找到BarTender可执行文件，请手动指定路径")
        return False
    
    # 启动BarTender
    logger.info("正在启动BarTender...")
    if not automator.start_bartender():
        logger.error("启动BarTender失败")
        return False
    
    # 等待应用程序完全启动
    import time
    time.sleep(5)
    
    # 测试目录
    test_dir = r'c:\Users\97088\Desktop\新建文件夹 (4)\商标集锦'
    if not os.path.exists(test_dir):
        logger.error(f"测试目录不存在: {test_dir}")
        return False
    
    # 获取目录下所有的BTW文件
    btw_files = [f for f in os.listdir(test_dir) if f.endswith('.btw')]
    if not btw_files:
        logger.error(f"测试目录下没有BTW文件: {test_dir}")
        return False
    
    logger.info(f"找到 {len(btw_files)} 个BTW文件，开始逐个测试...")
    
    # 只测试一个文件
    if btw_files:
        filename = btw_files[0]  # 只测试第一个文件
        file_path = os.path.join(test_dir, filename)
        logger.info(f"\n=== 测试文件: {filename} ===")
        
        try:
            # 打开文件
            if not automator.open_file(file_path):
                logger.error(f"打开文件失败: {filename}")
            else:
                # 等待文件完全打开
                time.sleep(3)
                
                # 处理可能出现的确定对话框 - 按回车键跳过
                logger.info("处理可能出现的确定对话框，按回车键...")
                import pyautogui
                pyautogui.press('enter')
                time.sleep(2)
                
                # 使用OCR识别并修改文字 - 测试"3712" → "371一"
                logger.info("正在测试OCR文字修改功能...")
                success = automator.ocr_modify_text("3712", "371一")
                
                if success:
                    logger.info(f"文件 {filename} 测试成功！")
                else:
                    logger.error(f"文件 {filename} 测试失败！")
                
                # 等待一下再继续
                time.sleep(3)
                
        except Exception as e:
            logger.error(f"测试文件 {filename} 时发生错误: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        # 关闭当前文件（不保存）
        logger.info(f"关闭文件 {filename}（不保存更改）...")
        # 使用Ctrl+F4关闭当前文件
        import pyautogui
        pyautogui.hotkey('ctrl', 'f4')
        time.sleep(2)
        
        # 如果弹出保存对话框，选择"不保存"
        try:
            pyautogui.press('n')  # 假设"不保存"是n键
            time.sleep(2)
        except Exception as e:
            logger.warning(f"关闭文件时处理保存对话框失败: {str(e)}")
    else:
        logger.error(f"测试目录下没有BTW文件: {test_dir}")
    
    # 关闭BarTender
    logger.info("所有文件测试完成，关闭BarTender...")
    # 发送Alt+F4关闭窗口
    import pyautogui
    pyautogui.hotkey('alt', 'f4')
    time.sleep(2)
    
    # 如果弹出保存对话框，选择"不保存"
    try:
        pyautogui.press('n')  # 假设"不保存"是n键
        time.sleep(2)
    except Exception as e:
        logger.warning(f"关闭BarTender时处理保存对话框失败: {str(e)}")
    
    logger.info("所有测试完成！")
    return True

if __name__ == "__main__":
    logger.info("开始测试商标集锦目录下的所有BTW文件")
    success = test_trademark_files()
    logger.info(f"商标集锦文件测试{'成功' if success else '失败'}")
    sys.exit(0 if success else 1)
