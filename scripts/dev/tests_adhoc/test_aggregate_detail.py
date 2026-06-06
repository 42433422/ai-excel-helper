"""详细测试聚合函数"""

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
raw = read_dingtalk_dataframe(source_file, sheet="打卡时间", header_row=2)
print(f"读取到 {len(raw)} 行数据")
print(f"raw.empty: {raw.empty}")

print(f"\n构建规范化数据...")
norm = build_normalized_frame(raw, month="2026-03")
print(f"规范化后行数：{len(norm)}")
print(f"norm.empty: {norm.empty}")

print(f"\n聚合月度统计...")
stats = aggregate_monthly_stats(norm, month="2026-03")
print(f"统计后行数：{len(stats)}")
print(f"stats.empty: {stats.empty}")
print(f"len(stats) 类型：{type(len(stats))}")

# 直接测试 len(stats)
result_len = len(stats)
print(f"result_len = {result_len}")
print(f"result_len 类型：{type(result_len)}")
