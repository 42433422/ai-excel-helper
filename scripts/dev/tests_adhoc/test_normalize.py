"""测试 build_normalized_frame 函数"""

import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

import pandas as pd
from pathlib import Path
from taiyangniao_attendance.convert import read_dingtalk_dataframe, build_normalized_frame

source_file = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")

print(f"读取钉钉数据...")
df = read_dingtalk_dataframe(source_file, sheet="打卡时间", header_row=2)
print(f"读取到 {len(df)} 行数据")
print(f"列数：{len(df.columns)}")
print(f"\n前 3 行:")
print(df.head(3))

print(f"\n构建规范化数据...")
norm_df = build_normalized_frame(df, month="2026-03")
print(f"规范化后行数：{len(norm_df)}")
print(f"规范化后列：{list(norm_df.columns)}")
print(f"\n前 5 行:")
print(norm_df.head())

print(f'\n非空行数：{len(norm_df[norm_df["上班打卡"].notna() | norm_df["下班打卡"].notna()])}')
