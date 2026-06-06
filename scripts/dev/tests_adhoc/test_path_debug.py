"""测试路径解析"""

import os
from pathlib import Path

root = Path(r"E:\FHD")
relpath = "424/考勤-2026-3月份考勤统计表.xlsx"

candidate = (root / relpath).resolve()
print(f"candidate: {candidate}")
print(f"is_file: {candidate.is_file()}")

parent_dir = candidate.parent
print(f"parent_dir: {parent_dir}")
print(f"parent exists: {parent_dir.exists()}")

try:
    dir_contents = os.listdir(str(parent_dir))
    print(f"dir_contents ({len(dir_contents)} files):")
    for f in dir_contents:
        if "考勤" in f:
            print(f"  '{f}'")
            print(f"    normalized: '{f.replace(' ', '')}'")
except Exception as e:
    print(f"os.listdir error: {e}")
