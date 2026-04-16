import os

folder = r'e:\FHD\424'
dir_contents = os.listdir(folder)

print(f'目录中的所有文件 ({len(dir_contents)} 个):')
for i, f in enumerate(dir_contents):
    if f.endswith('.xlsx') and not f.startswith('~$'):
        print(f'{i:3d}: {repr(f)}')
