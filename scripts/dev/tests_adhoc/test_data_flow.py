import pandas as pd
import os

folder = r"e:\FHD\424"
dingtalk_file = os.path.join(folder, "钉钉导出来的考勤数据.xlsx")

# 读取钉钉数据
print("=== 读取钉钉打卡时间数据 ===")
df = pd.read_excel(dingtalk_file, sheet_name="打卡时间", header=2)

# 清理数据 - 移除第 0 行（日期行）
df = df.iloc[1:].reset_index(drop=True)

print(f"员工数量：{len(df)}")
print(f"\n前 3 个员工的数据:")
for i in range(min(3, len(df))):
    print(f"\n员工 {i+1}:")
    row = df.iloc[i]
    print(f'  姓名：{row["姓名"]}')
    print(f'  部门：{row["部门"]}')
    print(f"  打卡时间数据 (前 10 天):")
    for j in range(7, min(17, len(row))):
        col_name = df.columns[j]
        value = row[col_name]
        if pd.notna(value) and str(value).strip():
            print(f"    {col_name}: {value}")
