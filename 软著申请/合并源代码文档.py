# -*- coding: utf-8 -*-
"""
合并前后端源代码文档
生成符合软著申请要求的完整源代码
"""

import os
from datetime import datetime


def count_lines(file_path: str) -> int:
    """统计文件行数"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return len(f.readlines())


def merge_source_code(output_file: str, *input_files):
    """合并多个源代码文件"""
    total_lines = 0
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("智能发货单生成系统 - 源代码文档\n")
        outfile.write("软件著作权申请专用\n")
        outfile.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write("=" * 80 + "\n\n")
        
        for input_file in input_files:
            if not os.path.exists(input_file):
                print(f"文件不存在：{input_file}")
                continue
                
            filename = os.path.basename(input_file)
            lines = count_lines(input_file)
            total_lines += lines
            
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write(f"文件：{filename}\n")
            outfile.write(f"行数：{lines}\n")
            outfile.write("=" * 80 + "\n\n")
            
            with open(input_file, 'r', encoding='utf-8') as infile:
                outfile.write(infile.read())
            
            outfile.write("\n\n")
            print(f"已合并：{filename} ({lines} 行)")
    
    print(f"\n合并完成！")
    print(f"总行数：{total_lines}")
    print(f"输出文件：{output_file}")
    
    return total_lines


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    frontend_file = os.path.join(base_dir, '前端源代码.txt')
    backend_file = os.path.join(base_dir, '后端源代码.txt')
    output_file = os.path.join(base_dir, '完整源代码.txt')
    
    total_lines = merge_source_code(output_file, frontend_file, backend_file)
    
    print(f"\n{'='*60}")
    print("软著申请源代码文档统计")
    print(f"{'='*60}")
    print(f"前端代码行数：{count_lines(frontend_file):,}")
    print(f"后端代码行数：{count_lines(backend_file):,}")
    print(f"总代码行数：{total_lines:,}")
    print(f"输出文件：{output_file}")
    print(f"{'='*60}")
