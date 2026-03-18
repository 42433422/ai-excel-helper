#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试标签生成和PDF转换功能
"""

import os
import logging
from label_generator import ProductLabelGenerator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🔍 开始测试标签生成和PDF转换功能...")
    
    # 获取当前目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
    
    logger.info(f"商标导出目录: {LABELS_EXPORT_DIR}")
    
    # 确保目录存在
    os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
    
    # 1. 清理旧文件
    logger.info("🧹 清理旧文件...")
    generator = ProductLabelGenerator()
    generator.cleanup_old_pdfs(LABELS_EXPORT_DIR)
    
    # 检查清理结果
    remaining_files = []
    if os.path.exists(LABELS_EXPORT_DIR):
        remaining_files = [f for f in os.listdir(LABELS_EXPORT_DIR) if os.path.isfile(os.path.join(LABELS_EXPORT_DIR, f))]
    
    logger.info(f"清理后剩余文件: {len(remaining_files)} 个")
    
    # 2. 生成测试标签
    logger.info("\n🏷️ 生成测试标签...")
    
    # 准备测试数据
    test_data = {
        'product_number': 'TEST-001',
        'product_name': '测试产品',
        'ratio': '主剂：固化剂：稀释剂，1：0.7-0.8：0.5-0.7',
        'production_date': '2026.02.09',
        'shelf_life': '6个月',
        'specification': '10±0.1KG',
        'inspector': '合格'
    }
    
    # 生成标签路径
    output_path = os.path.join(LABELS_EXPORT_DIR, 'test_label.png')
    
    # 生成标签
    result_path = generator.generate_label(test_data, output_path)
    logger.info(f"生成结果: {result_path}")
    
    # 3. 验证结果
    logger.info("\n🔍 验证结果...")
    
    # 检查生成的文件
    generated_files = []
    if os.path.exists(LABELS_EXPORT_DIR):
        generated_files = [f for f in os.listdir(LABELS_EXPORT_DIR) if os.path.isfile(os.path.join(LABELS_EXPORT_DIR, f))]
    
    logger.info(f"生成的文件: {len(generated_files)} 个")
    for file in generated_files:
        logger.info(f"  - {file}")
        # 检查文件类型
        if file.endswith('.pdf'):
            logger.info(f"    ✅ 是PDF文件")
        elif file.endswith('.png'):
            logger.info(f"    ⚠️  是PNG文件（转换可能失败）")
    
    # 4. 验证PDF转换
    pdf_files = [f for f in generated_files if f.endswith('.pdf')]
    png_files = [f for f in generated_files if f.endswith('.png')]
    
    logger.info(f"\n📊 转换结果:")
    logger.info(f"✅ PDF文件: {len(pdf_files)} 个")
    logger.info(f"⚠️  PNG文件: {len(png_files)} 个")
    
    if pdf_files and not png_files:
        logger.info("✅ 转换成功！只保留了PDF文件")
    elif pdf_files and png_files:
        logger.warning("⚠️  转换部分成功，同时保留了PDF和PNG文件")
    elif not pdf_files and png_files:
        logger.error("❌ 转换失败，只保留了PNG文件")
    else:
        logger.error("❌ 没有生成任何文件")
    
    # 5. 测试清理旧PDF
    logger.info("\n🧹 测试清理旧PDF文件...")
    generator.cleanup_old_pdfs(LABELS_EXPORT_DIR)
    
    # 检查清理结果
    final_files = []
    if os.path.exists(LABELS_EXPORT_DIR):
        final_files = [f for f in os.listdir(LABELS_EXPORT_DIR) if os.path.isfile(os.path.join(LABELS_EXPORT_DIR, f))]
    
    logger.info(f"清理后剩余文件: {len(final_files)} 个")
    for file in final_files:
        logger.info(f"  - {file}")
    
    if not final_files:
        logger.info("✅ 清理成功！目录已完全清空")
    else:
        logger.warning("⚠️  清理不完全，目录中仍有文件")
    
    logger.info("\n🎉 测试完成！标签生成和PDF转换功能测试结束")
