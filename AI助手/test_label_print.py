#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试标签打印功能
"""

import os
import logging
from pdf_label_printer import print_pdf_labels

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

# 获取PDF文件目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, 'PDF文件')

# 查找标签PDF文件
def find_label_pdf():
    """查找PDF目录中的标签PDF文件"""
    try:
        if not os.path.exists(PDF_DIR):
            logger.error(f"PDF目录不存在: {PDF_DIR}")
            return None
        
        pdf_files = []
        for file in os.listdir(PDF_DIR):
            if file.endswith('.pdf') and ('标签' in file or 'label' in file.lower()):
                pdf_files.append(os.path.join(PDF_DIR, file))
        
        if not pdf_files:
            logger.error("未找到标签PDF文件")
            return None
        
        logger.info(f"找到 {len(pdf_files)} 个标签PDF文件")
        for pdf_file in pdf_files:
            logger.info(f"  - {os.path.basename(pdf_file)}")
        
        return pdf_files[0]  # 返回第一个找到的标签PDF文件
    except Exception as e:
        logger.error(f"查找标签PDF文件失败: {e}")
        return None

# 测试标签打印
def test_label_print():
    """测试标签打印功能"""
    try:
        logger.info("🔍 开始测试标签打印功能...")
        
        # 查找标签PDF文件
        label_pdf_path = find_label_pdf()
        if not label_pdf_path:
            logger.error("❌ 未找到标签PDF文件，测试失败")
            return False
        
        logger.info(f"📄 准备打印标签PDF: {os.path.basename(label_pdf_path)}")
        
        # 打印标签，显示应用窗口以便监控
        logger.info("📤 发送打印命令...")
        label_print_result = print_pdf_labels(label_pdf_path, show_app=True)
        
        if label_print_result.get('success', False):
            logger.info("✅ 标签打印测试成功！")
            logger.info(f"📋 打印结果: {label_print_result}")
            return True
        else:
            logger.error(f"❌ 标签打印测试失败: {label_print_result.get('message')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_label_print()
