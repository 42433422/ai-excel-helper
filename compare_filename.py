import os

folder = r'e:\FHD\424'
file_name = '考勤 -2026-3 月份考勤统计表.xlsx'

dir_contents = os.listdir(folder)

print(f'查找的文件名：{file_name}')
print(f'文件名 bytes: {file_name.encode("utf-8")}')
print(f'文件名 repr: {repr(file_name)}')

print(f'\n目录中的文件:')
for f in dir_contents:
    if '考勤统计' in f:
        print(f'  {f}')
        print(f'    bytes: {f.encode("utf-8")}')
        print(f'    repr: {repr(f)}')
        print(f'    相等：{f == file_name}')
