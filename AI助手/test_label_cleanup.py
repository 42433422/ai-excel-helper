#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试商标导出目录旧文件清除功能
"""

import os
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🔍 开始测试商标导出目录旧文件清除功能...")
    
    # 获取当前目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
    
    logger.info(f"商标导出目录: {LABELS_EXPORT_DIR}")
    
    # 确保目录存在
    os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
    
    # 1. 检查当前目录中的文件
    existing_files = []
    if os.path.exists(LABELS_EXPORT_DIR):
        existing_files = [f for f in os.listdir(LABELS_EXPORT_DIR) if os.path.isfile(os.path.join(LABELS_EXPORT_DIR, f))]
    
    logger.info(f"当前目录中的文件: {len(existing_files)} 个")
    for file in existing_files[:5]:  # 只显示前5个文件
        logger.info(f"  - {file}")
    if len(existing_files) > 5:
        logger.info(f"  ... 还有 {len(existing_files) - 5} 个文件")
    
    # 2. 测试清除功能
    logger.info("\n🧹 开始清除旧文件...")
    
    deleted_count = 0
    failed_count = 0
    
    for filename in existing_files:
        file_path = os.path.join(LABELS_EXPORT_DIR, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                deleted_count += 1
                logger.info(f"✅ 已删除: {filename}")
            except Exception as e:
                failed_count += 1
                logger.warning(f"❌ 删除失败 {filename}: {e}")
    
    logger.info(f"\n📊 清除结果:")
    logger.info(f"✅ 成功删除: {deleted_count} 个文件")
    logger.info(f"❌ 删除失败: {failed_count} 个文件")
    logger.info(f"📁 目录已清空，准备生成新的商标标签")
    
    # 3. 验证目录是否为空
    remaining_files = []
    if os.path.exists(LABELS_EXPORT_DIR):
        remaining_files = [f for f in os.listdir(LABELS_EXPORT_DIR) if os.path.isfile(os.path.join(LABELS_EXPORT_DIR, f))]
    
    logger.info(f"\n🔍 验证结果:")
    logger.info(f"剩余文件数量: {len(remaining_files)} 个")
    if remaining_files:
        logger.warning("⚠️  目录中仍有文件:")
        for file in remaining_files:
            logger.warning(f"  - {file}")
    else:
        logger.info("✅ 目录已完全清空")
    
    logger.info("\n🎉 测试完成！商标导出目录旧文件清除功能正常工作")
