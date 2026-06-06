"""测试路径解析"""

import sys
import os

# 设置环境变量
os.environ["WORKSPACE_ROOT"] = r"e:\FHD"

sys.path.insert(0, r"e:\FHD\backend\shell")

from taiyangniao_attendance.paths import resolve_workspace_excel

# 测试路径
template_relpath = "424/考勤 -2026-3 月份考勤统计表.xlsx"

print(f"测试路径：{template_relpath}")
print(f'WORKSPACE_ROOT: {os.environ["WORKSPACE_ROOT"]}')

try:
    template_path = resolve_workspace_excel(template_relpath)
    print(f"✓ 解析成功：{template_path}")
    print(f"  类型：{type(template_path)}")
    print(f"  is_file(): {template_path.is_file()}")
    print(f"  parent: {template_path.parent}")
    print(f"  name: {template_path.name}")

    # 手动验证
    parent_dir = template_path.parent
    file_name = template_path.name
    print(f"\n手动验证:")
    print(f"  父目录：{parent_dir}")
    print(f"  文件名：{file_name}")
    print(f"  文件名 repr: {repr(file_name)}")

    dir_contents = os.listdir(str(parent_dir))
    normalized_file_name = file_name.replace(" ", "")
    print(f"  标准化文件名：{normalized_file_name}")

    found = False
    for f in dir_contents:
        if f.replace(" ", "") == normalized_file_name:
            print(f"  ✓ 找到匹配文件：{f}")
            found = True
            break

    if not found:
        print(f"  ✗ 未找到匹配文件")

except Exception as e:
    print(f"✗ 解析失败：{e}")
    import traceback

    traceback.print_exc()
