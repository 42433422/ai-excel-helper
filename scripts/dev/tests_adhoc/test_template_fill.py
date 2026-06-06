"""测试从钉钉数据填充模板的完整流程"""

import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

from pathlib import Path
from taiyangniao_attendance.convert import (
    read_dingtalk_dataframe,
    build_normalized_frame,
    aggregate_monthly_stats,
    _write_workbook_to_path,
)

# 输入文件
dingtalk_file = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")
template_file = Path(r"e:\FHD\424\考勤 -2026-3 月份考勤统计表.xlsx")  # 注意：文件名中没有空格
output_file = Path(r"e:\FHD\424\测试输出.xlsx")

print("=== 开始测试 ===")
print(f"输入文件：{dingtalk_file}")
print(f"模板文件：{template_file}")
print(f"输出文件：{output_file}")

# 步骤 1: 读取钉钉数据
print("\n1. 读取钉钉数据...")
raw_df = read_dingtalk_dataframe(dingtalk_file, header_row=2)
print(f"   读取到 {len(raw_df)} 行数据")

# 步骤 2: 构建规范化数据
print("\n2. 构建规范化数据...")
norm_df = build_normalized_frame(raw_df, month="2026-03")
print(f"   规范化后 {len(norm_df)} 行数据")
print(f"   列：{norm_df.columns.tolist()[:10]}...")

# 步骤 3: 聚合月度统计
print("\n3. 聚合月度统计...")
stats_df = aggregate_monthly_stats(norm_df, month="2026-03")
print(f"   统计后 {len(stats_df)} 行数据")

# 步骤 4: 写入模板
print("\n4. 写入模板...")
_write_workbook_to_path(stats_df, output_file, template_path=template_file, dingtalk_detail=norm_df)
print(f"   完成！输出文件：{output_file}")

print("\n=== 测试完成 ===")
