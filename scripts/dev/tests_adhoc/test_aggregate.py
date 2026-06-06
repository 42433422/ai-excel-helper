"""测试聚合函数"""

import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

import pandas as pd
from pathlib import Path
from taiyangniao_attendance.convert import (
    read_dingtalk_dataframe,
    build_normalized_frame,
    aggregate_monthly_stats,
)

source_file = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")

print(f"读取钉钉数据...")
df = read_dingtalk_dataframe(source_file, sheet="打卡时间", header_row=2)
print(f"读取到 {len(df)} 行数据")

print(f"\n构建规范化数据...")
norm_df = build_normalized_frame(df, month="2026-03")
print(f"规范化后行数：{len(norm_df)}")

print(f"\n聚合月度统计...")
stats_df = aggregate_monthly_stats(norm_df, month="2026-03")
print(f"统计后行数：{len(stats_df)}")
print(f"统计列：{list(stats_df.columns)}")
print(f"\n前 5 行:")
print(stats_df.head())
