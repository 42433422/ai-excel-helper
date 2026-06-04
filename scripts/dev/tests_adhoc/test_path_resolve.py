"""调试路径解析"""

import sys

sys.path.insert(0, r"e:\FHD\backend\shell")

from taiyangniao_attendance.paths import resolve_workspace_excel, workspace_root
import os

print(f'WORKSPACE_ROOT: {os.environ.get("WORKSPACE_ROOT", "未设置")}')
print(f"workspace_root(): {workspace_root()}")

# 测试路径解析
template_relpath = "424/考勤 -2026-3 月份考勤统计表.xlsx"
print(f"\n测试路径：{template_relpath}")

try:
    template_path = resolve_workspace_excel(template_relpath)
    print(f"解析成功：{template_path}")
    print(f"is_file(): {template_path.is_file()}")

    # 手动检查
    parent_dir = template_path.parent
    file_name = template_path.name
    print(f"\n父目录：{parent_dir}")
    print(f"文件名：{file_name}")
    print(f"文件名 repr: {repr(file_name)}")

    dir_contents = os.listdir(str(parent_dir))
    print(f"\n目录中的文件数：{len(dir_contents)}")

    normalized_file_name = file_name.replace(" ", "")
    print(f"标准化文件名：{normalized_file_name}")

    for f in dir_contents:
        if "考勤统计" in f:
            print(f"  匹配文件：{f}")
            print(f"    repr: {repr(f)}")
            print(f'    标准化：{f.replace(" ", "")}')
            print(f'    匹配：{f.replace(" ", "") == normalized_file_name}')

except Exception as e:
    print(f"解析失败：{e}")
    import traceback

    traceback.print_exc()
