#!/usr/bin/env python3
import os
import glob

# 检查unit_databases目录
units_dir = 'unit_databases'
print(f'=== 检查目录: {units_dir} ===')
if os.path.exists(units_dir):
    print(f'目录存在')
    db_files = glob.glob(os.path.join(units_dir, '*.db'))
    print(f'找到的数据库文件:')
    for db_file in db_files:
        db_name = os.path.basename(db_file)
        print(f'  - {db_name} -> {db_file}')
else:
    print(f'目录不存在')

# 模拟AI解析器的加载逻辑
print('\n=== 模拟单位数据库加载 ===')
unit_databases = {}
try:
    units_dir = os.path.join(os.path.dirname(os.path.abspath('ai_augmented_parser.py')), 'unit_databases')
    print(f'查找目录: {units_dir}')
    
    if os.path.exists(units_dir):
        db_files = glob.glob(os.path.join(units_dir, '*.db'))
        print(f'找到的数据库文件: {len(db_files)} 个')
        
        for db_path in db_files:
            db_name = os.path.splitext(os.path.basename(db_path))[0]
            unit_databases[db_name] = db_path
            print(f'  {db_name} -> {db_path}')
    else:
        print(f'目录不存在: {units_dir}')
        
except Exception as e:
    print(f'加载单位数据库时出错: {e}')

print('\n=== 测试单位匹配 ===')
test_units = ['七彩乐园', 'qicaidian', '七彩']
for test_unit in test_units:
    if test_unit in unit_databases:
        print(f'精确匹配: {test_unit} -> {unit_databases[test_unit]}')
    else:
        print(f'未找到精确匹配: {test_unit}')
        # 检查智能匹配
        for db_name in unit_databases.keys():
            if test_unit in db_name:
                print(f'  智能匹配: {test_unit} -> {db_name}')
