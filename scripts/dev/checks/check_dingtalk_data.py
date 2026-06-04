import pandas as pd
import os

folder = r"e:\FHD\424"
dingtalk_file = os.path.join(folder, "钉钉导出来的考勤数据.xlsx")

# 读取钉钉数据
print("=== 读取钉钉打卡时间数据 ===")
df = pd.read_excel(dingtalk_file, sheet_name="打卡时间", header=2)
print(f"列名：{df.columns.tolist()}")
print(f"\n前 5 行数据:")
print(df.head())

# 查看数据结构
print(f"\n数据形状：{df.shape}")
print(f"\n列类型:")
print(df.dtypes)

# 查看第一个员工的数据
print(f"\n第一个员工的完整数据:")
print(df.iloc[0])
