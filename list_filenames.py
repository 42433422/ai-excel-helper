"""查看实际文件名"""
import os

dir_path = r'e:\FHD\424'
files = os.listdir(dir_path)

print("所有包含'考勤'的文件:")
for f in files:
    if '考勤' in f:
        print(f"  '{f}' (len={len(f)}, bytes={f.encode('utf-8')})")
