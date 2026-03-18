#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整理PDF文件到专门的文件夹
"""

import os
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def organize_pdf_files():
    """
    整理现有PDF文件到专门的文件夹
    """
    print("=" * 60)
    print("📁 PDF文件整理工具")
    print("=" * 60)
    
    # 创建PDF文件夹
    pdf_dir = "PDF文件"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        print(f"✅ 创建PDF文件夹: {pdf_dir}")
    
    # 查找所有PDF文件
    pdf_files = []
    for file in os.listdir('.'):
        if file.lower().endswith('.pdf'):
            pdf_files.append(file)
    
    if not pdf_files:
        print("📄 未找到任何PDF文件")
        return
    
    print(f"\n📄 找到 {len(pdf_files)} 个PDF文件:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file}")
    
    # 移动PDF文件到专门文件夹
    moved_count = 0
    for pdf_file in pdf_files:
        source_path = pdf_file
        dest_path = os.path.join(pdf_dir, pdf_file)
        
        try:
            if os.path.exists(dest_path):
                print(f"  ⚠️  目标文件已存在，跳过: {pdf_file}")
                continue
            
            shutil.move(source_path, dest_path)
            print(f"  ✅ 移动: {pdf_file} → {pdf_dir}/")
            moved_count += 1
            
        except Exception as e:
            print(f"  ❌ 移动失败: {pdf_file} - {e}")
    
    print(f"\n📊 整理完成:")
    print(f"  移动PDF文件: {moved_count} 个")
    print(f"  PDF文件夹: {pdf_dir}")
    
    # 验证移动结果
    remaining_pdf = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    moved_pdf = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    print(f"\n🔍 验证结果:")
    print(f"  根目录剩余PDF: {len(remaining_pdf)} 个")
    print(f"  PDF文件夹内PDF: {len(moved_pdf)} 个")
    
    if moved_pdf:
        print(f"\n📋 PDF文件夹内容:")
        for pdf_file in moved_pdf:
            size = os.path.getsize(os.path.join(pdf_dir, pdf_file)) / 1024
            print(f"  - {pdf_file} ({size:.1f} KB)")
    
    print("\n" + "=" * 60)
    print("PDF文件整理完成")
    print("=" * 60)

if __name__ == "__main__":
    organize_pdf_files()
