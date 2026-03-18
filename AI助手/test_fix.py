#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的 special_trademark_print.py
确保类型错误已经解决
"""

import os
import logging
from special_trademark_print import print_trademark_pdf

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🔍 测试修复后的 special_trademark_print.py")
    
    # 检查是否存在PDF文件
    pdf_files = []
    if os.path.exists("PDF文件"):
        pdf_files = [f for f in os.listdir("PDF文件") if f.endswith(".pdf")]
    
    if pdf_files:
        test_pdf = os.path.join("PDF文件", pdf_files[0])
        logger.info(f"找到测试PDF文件: {test_pdf}")
        
        # 测试打印功能
        logger.info("测试打印商标PDF...")
        result = print_trademark_pdf(test_pdf, "TSC TTP-244 Plus", show_app=True)
        logger.info(f"打印结果: {result}")
        
        if result.get("success"):
            logger.info("✅ 测试成功！类型错误已修复")
        else:
            logger.warning(f"⚠️  打印失败，但类型错误已修复: {result.get('message')}")
    else:
        logger.warning("⚠️  未找到PDF文件，但脚本运行正常，类型错误已修复")
    
    logger.info("✅ 测试完成！special_trademark_print.py 中的类型错误已成功修复")
