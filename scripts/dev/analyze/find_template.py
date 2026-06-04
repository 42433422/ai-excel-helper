import os

folder = r"e:\FHD\424"
files = os.listdir(folder)

print("424 目录中的所有文件:")
for f in files:
    if f.endswith(".xlsx") and not f.startswith("~$"):
        print(f"  {f}")

# 找到模板文件
template_files = [
    f for f in files if f.endswith(".xlsx") and "考勤统计表" in f and not f.startswith("~$")
]
print(f"\n模板文件：{template_files}")

if template_files:
    full_path = os.path.join(folder, template_files[0])
    print(f"完整路径：{full_path}")
    print(f"文件存在：{os.path.exists(full_path)}")
