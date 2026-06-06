"""检查钉钉导出文件的格式"""

import pandas as pd
import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

from taiyangniao_attendance.convert import read_dingtalk_dataframe, _auto_detect_header_row
from pathlib import Path

source_file = Path(r"e:\FHD\424\钉钉导出来的考勤数据.xlsx")

print(f"检查文件：{source_file}")
print(f"文件存在：{source_file.exists()}")

# 读取原始数据
print("\n=== 读取原始数据 ===")
raw_df = pd.read_excel(source_file, sheet_name="打卡时间", header=None, engine="openpyxl")
print(f"总行数：{len(raw_df)}")
print(f"总列数：{len(raw_df.columns)}")

# 显示前 10 行
print("\n前 10 行:")
for i in range(min(10, len(raw_df))):
    row_values = [str(v) if pd.notna(v) else "None" for v in raw_df.iloc[i].tolist()]
    print(f"Row {i}: {row_values[:10]}...")  # 只显示前 10 列

# 自动检测表头行
print("\n=== 自动检测表头行 ===")
header_row = _auto_detect_header_row(source_file, "打卡时间")
print(f"检测到的表头行：{header_row}")

# 读取数据
print("\n=== 读取数据 ===")
df = read_dingtalk_dataframe(source_file, sheet="打卡时间", header_row=header_row)
print(f"读取到 {len(df)} 行数据")
print(f"列名：{list(df.columns)}")

# 显示前 5 行
print("\n前 5 行数据:")
print(df.head())
