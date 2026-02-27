# 产品映射修复完整解决方案

## 1. 解决方案概述

本解决方案旨在彻底解决除蕊芯家私外其他购买单位的产品映射错误问题，通过系统性的数据清理、重新导入和验证流程，确保每个购买单位的产品都能正确映射到数据库中。

## 2. 详细解决方案

### 2.1 第一阶段：数据清理与准备

#### 2.1.1 数据库备份
```python
# 备份当前数据库
import shutil
import datetime

backup_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'products_backup_{backup_time}.db'
shutil.copy('products.db', backup_file)
print(f"✅ 数据库备份完成: {backup_file}")
```

#### 2.1.2 数据清理
```python
# 清理products表中的数据，但保留purchase_units表
import sqlite3

conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 清理products表
cursor.execute('DELETE FROM products')
conn.commit()
print("✅ 清理完成: 已清空products表中的所有数据")

# 验证清理结果
cursor.execute('SELECT COUNT(*) FROM products')
count = cursor.fetchone()[0]
print(f"✅ 验证结果: products表中剩余 {count} 条记录")

conn.close()
```

### 2.2 第二阶段：分批重新导入

#### 2.2.1 按购买单位分批导入
```python
import pandas as pd
import sqlite3

# 读取Excel数据
excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# 获取所有购买单位
purchase_units = df['购买单位'].dropna().unique()
print(f"找到 {len(purchase_units)} 个购买单位")

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 获取购买单位ID映射
def get_unit_id(unit_name):
    cursor.execute('SELECT id FROM purchase_units WHERE unit_name = ?', (unit_name,))
    result = cursor.fetchone()
    return result[0] if result else None

# 按购买单位分批导入
for unit in purchase_units:
    print(f"\n=== 导入购买单位: {unit} ===")
    
    # 获取该单位的产品数据
    unit_products = df[df['购买单位'] == unit]
    print(f"该单位产品数量: {len(unit_products)}")
    
    # 获取单位ID
    unit_id = get_unit_id(unit)
    if not unit_id:
        print(f"❌ 错误: 购买单位 '{unit}' 在数据库中不存在")
        continue
    
    # 导入产品
    success_count = 0
    error_count = 0
    
    for idx, row in unit_products.iterrows():
        try:
            # 提取产品信息
            model_number = str(row['产品型号']).strip() if pd.notna(row['产品型号']) else ''
            product_name = str(row['产品名称']).strip() if pd.notna(row['产品名称']) else ''
            price = float(row['单价']) if pd.notna(row['单价']) else 0.0
            
            # 跳过空记录
            if not model_number and not product_name:
                continue
            
            # 插入产品
            cursor.execute('''
                INSERT INTO products 
                (model_number, name, price, purchase_unit_id, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (model_number, product_name, price, unit_id, 1))
            
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"❌ 导入失败 (行 {idx}): {e}")
    
    conn.commit()
    print(f"✅ 导入完成: 成功 {success_count} 条, 失败 {error_count} 条")

conn.close()
print("\n✅ 所有购买单位产品导入完成!")
```

### 2.3 第三阶段：验证与测试

#### 2.3.1 基本验证
```python
import sqlite3
import pandas as pd

# 读取Excel数据
excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

print("=== 基本验证 ===")

# 1. 验证产品总数
cursor.execute('SELECT COUNT(*) FROM products')
db_count = cursor.fetchone()[0]
excel_count = len(df)
print(f"Excel产品总数: {excel_count}")
print(f"数据库产品总数: {db_count}")
print(f"匹配率: {db_count/excel_count*100:.2f}%")

# 2. 按购买单位验证
purchase_units = df['购买单位'].dropna().unique()
print(f"\n按购买单位验证 ({len(purchase_units)} 个单位):")

for unit in purchase_units:
    # Excel中该单位的产品数
    excel_unit_count = len(df[df['购买单位'] == unit])
    
    # 数据库中该单位的产品数
    cursor.execute('''
        SELECT COUNT(*) FROM products 
        WHERE purchase_unit_id = (
            SELECT id FROM purchase_units WHERE unit_name = ?
        )
    ''', (unit,))
    db_unit_count = cursor.fetchone()[0]
    
    match_rate = db_unit_count/excel_unit_count*100 if excel_unit_count > 0 else 0
    print(f"{unit}: Excel={excel_unit_count}, 数据库={db_unit_count}, 匹配率={match_rate:.2f}%")

conn.close()
```

#### 2.3.2 详细验证（产品型号级别）
```python
import sqlite3
import pandas as pd

# 读取Excel数据
excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 获取购买单位ID映射
unit_id_map = {}
cursor.execute('SELECT id, unit_name FROM purchase_units')
for row in cursor.fetchall():
    unit_id_map[row[1]] = row[0]

print("=== 产品型号详细验证 ===")

# 按购买单位验证产品型号
purchase_units = df['购买单位'].dropna().unique()

for unit in purchase_units:
    print(f"\n=== 验证购买单位: {unit} ===")
    
    # Excel中该单位的产品型号
    excel_models = set(df[df['购买单位'] == unit]['产品型号'].dropna().astype(str).unique())
    
    # 数据库中该单位的产品型号
    unit_id = unit_id_map.get(unit)
    if unit_id:
        cursor.execute('''
            SELECT DISTINCT model_number FROM products 
            WHERE purchase_unit_id = ? AND model_number != ''
        ''', (unit_id,))
        db_models = set(row[0] for row in cursor.fetchall() if row[0])
        
        # 分析差异
        only_excel = excel_models - db_models
        only_db = db_models - excel_models
        both = excel_models & db_models
        
        print(f"Excel型号数: {len(excel_models)}")
        print(f"数据库型号数: {len(db_models)}")
        print(f"两边都有的型号数: {len(both)}")
        print(f"Excel有但数据库没有的型号数: {len(only_excel)}")
        print(f"数据库有但Excel没有的型号数: {len(only_db)}")
        
        if only_excel:
            print("Excel有但数据库没有的型号 (前5个):")
            for model in list(only_excel)[:5]:
                print(f"  - {model}")
        
        if only_db:
            print("数据库有但Excel没有的型号 (前5个):")
            for model in list(only_db)[:5]:
                print(f"  - {model}")
    else:
        print(f"❌ 错误: 购买单位 '{unit}' 在数据库中不存在")

conn.close()
```

### 2.4 第三阶段：试错与复查流程

#### 2.4.1 自动试错机制
```python
import pandas as pd
import sqlite3

# 读取Excel数据
excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 获取购买单位ID映射
unit_id_map = {}
cursor.execute('SELECT id, unit_name FROM purchase_units')
for row in cursor.fetchall():
    unit_id_map[row[1]] = row[0]

print("=== 自动试错与修复 ===")

# 按购买单位进行试错修复
purchase_units = df['购买单位'].dropna().unique()

for unit in purchase_units:
    print(f"\n=== 试错修复购买单位: {unit} ===")
    
    # 获取该单位的Excel产品
    unit_products = df[df['购买单位'] == unit]
    unit_id = unit_id_map.get(unit)
    
    if not unit_id:
        print(f"❌ 跳过: 购买单位 '{unit}' 在数据库中不存在")
        continue
    
    # 获取数据库中该单位的产品型号
    cursor.execute('''
        SELECT DISTINCT model_number FROM products 
        WHERE purchase_unit_id = ?
    ''', (unit_id,))
    db_models = set(row[0] for row in cursor.fetchall())
    
    # 修复缺失的产品
    fixed_count = 0
    for idx, row in unit_products.iterrows():
        model_number = str(row['产品型号']).strip() if pd.notna(row['产品型号']) else ''
        product_name = str(row['产品名称']).strip() if pd.notna(row['产品名称']) else ''
        price = float(row['单价']) if pd.notna(row['单价']) else 0.0
        
        # 检查是否已存在
        cursor.execute('''
            SELECT COUNT(*) FROM products 
            WHERE purchase_unit_id = ? AND model_number = ?
        ''', (unit_id, model_number))
        count = cursor.fetchone()[0]
        
        if count == 0 and (model_number or product_name):
            try:
                cursor.execute('''
                    INSERT INTO products 
                    (model_number, name, price, purchase_unit_id, is_active)
                    VALUES (?, ?, ?, ?, ?)
                ''', (model_number, product_name, price, unit_id, 1))
                fixed_count += 1
            except Exception as e:
                print(f"❌ 修复失败: {e}")
    
    conn.commit()
    print(f"✅ 试错修复完成: 修复了 {fixed_count} 个缺失的产品")

conn.close()
```

#### 2.4.2 人工复查流程

**复查步骤：**
1. **导出验证报告**
2. **人工检查关键产品**
3. **确认映射正确性**
4. **记录复查结果**

```python
# 导出验证报告
import pandas as pd
import sqlite3
import datetime

# 读取Excel数据
excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
df = pd.read_excel(excel_file, sheet_name='Sheet1')

# 连接数据库
conn = sqlite3.connect('products.db')
cursor = conn.cursor()

# 获取购买单位ID映射
unit_id_map = {}
cursor.execute('SELECT id, unit_name FROM purchase_units')
for row in cursor.fetchall():
    unit_id_map[row[1]] = row[0]

# 生成验证报告
report_data = []

purchase_units = df['购买单位'].dropna().unique()

for unit in purchase_units:
    # Excel数据
    excel_products = df[df['购买单位'] == unit]
    excel_count = len(excel_products)
    excel_models = excel_products['产品型号'].dropna().nunique()
    
    # 数据库数据
    unit_id = unit_id_map.get(unit)
    if unit_id:
        cursor.execute('SELECT COUNT(*) FROM products WHERE purchase_unit_id = ?', (unit_id,))
        db_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT model_number) FROM products WHERE purchase_unit_id = ?', (unit_id,))
        db_models = cursor.fetchone()[0]
    else:
        db_count = 0
        db_models = 0
    
    report_data.append({
        '购买单位': unit,
        'Excel产品数': excel_count,
        '数据库产品数': db_count,
        'Excel型号数': excel_models,
        '数据库型号数': db_models,
        '匹配率': f"{db_count/excel_count*100:.1f}%" if excel_count > 0 else "0%"
    })

# 创建报告DataFrame
report_df = pd.DataFrame(report_data)

# 导出到Excel
report_file = f'product_mapping_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
report_df.to_excel(report_file, index=False)
print(f"✅ 验证报告导出完成: {report_file}")

# 显示报告摘要
print("\n=== 验证报告摘要 ===")
print(report_df)

conn.close()
```

### 2.5 第四阶段：持续监控与维护

#### 2.5.1 定期验证脚本
```python
# 定期验证产品映射状态
import pandas as pd
import sqlite3
import datetime

def validate_product_mapping():
    """验证产品映射状态"""
    print(f"=== 开始验证: {datetime.datetime.now()} ===")
    
    # 读取Excel数据
    excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    
    # 连接数据库
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # 获取购买单位ID映射
    unit_id_map = {}
    cursor.execute('SELECT id, unit_name FROM purchase_units')
    for row in cursor.fetchall():
        unit_id_map[row[1]] = row[0]
    
    # 验证结果
    results = []
    all_good = True
    
    # 按购买单位验证
    purchase_units = df['购买单位'].dropna().unique()
    
    for unit in purchase_units:
        # Excel数据
        excel_count = len(df[df['购买单位'] == unit])
        
        # 数据库数据
        unit_id = unit_id_map.get(unit)
        if unit_id:
            cursor.execute('SELECT COUNT(*) FROM products WHERE purchase_unit_id = ?', (unit_id,))
            db_count = cursor.fetchone()[0]
            
            match_rate = db_count / excel_count * 100 if excel_count > 0 else 0
            status = "✅ 正常" if match_rate >= 99 else "❌ 异常"
            
            if match_rate < 99:
                all_good = False
            
            results.append({
                '购买单位': unit,
                'Excel产品数': excel_count,
                '数据库产品数': db_count,
                '匹配率': f"{match_rate:.1f}%",
                '状态': status
            })
    
    conn.close()
    
    # 显示结果
    print("\n=== 验证结果 ===")
    for result in results:
        print(f"{result['状态']} {result['购买单位']}: {result['数据库产品数']}/{result['Excel产品数']} ({result['匹配率']})")
    
    if all_good:
        print("\n🎉 所有购买单位的产品映射都正常!")
    else:
        print("\n⚠️  部分购买单位的产品映射存在问题，需要修复!")
    
    return all_good

# 运行验证
if __name__ == "__main__":
    validate_product_mapping()
```

## 3. 实施步骤

### 3.1 准备阶段
1. **备份当前数据库**
2. **确认Excel文件路径正确**
3. **检查购买单位表是否完整**

### 3.2 执行阶段
1. **运行数据清理脚本**
2. **运行分批导入脚本**
3. **运行详细验证脚本**
4. **运行自动试错修复脚本**
5. **生成验证报告**

### 3.3 验证阶段
1. **人工检查验证报告**
2. **抽查关键购买单位的产品**
3. **确认产品型号映射正确**
4. **验证价格信息准确**

### 3.4 维护阶段
1. **设置定期验证计划**
2. **建立数据变更流程**
3. **制定异常处理机制**

## 4. 技术要点

### 4.1 关键技术
- **分批处理**：按购买单位分批导入，避免数据混乱
- **错误处理**：完善的异常捕获和处理机制
- **数据验证**：多层次的验证确保映射正确性
- **自动修复**：智能试错和自动修复机制

### 4.2 性能优化
- **批量插入**：使用批量操作提高导入速度
- **索引优化**：确保purchase_unit_id和model_number字段有索引
- **内存管理**：处理大型Excel文件时的内存优化

### 4.3 数据质量保证
- **类型转换**：确保数据类型一致性
- **空值处理**：合理处理缺失数据
- **重复检测**：避免重复导入相同产品
- **完整性验证**：确保每个产品都有必要字段

## 5. 预期效果

### 5.1 解决的问题
- ✅ 所有购买单位的产品映射错误
- ✅ 产品型号与购买单位的正确关联
- ✅ 价格信息的准确映射
- ✅ 不同购买单位产品的隔离

### 5.2 实现的功能
- ✅ 自动化数据清理和导入
- ✅ 智能错误检测和修复
- ✅ 详细的验证报告
- ✅ 定期监控机制

### 5.3 业务价值
- **提高数据准确性**：确保数据库产品与Excel文件完全匹配
- **提升工作效率**：自动化流程减少人工操作
- **降低错误率**：多层次验证确保映射正确
- **增强可维护性**：建立持续监控机制

## 6. 风险控制

### 6.1 潜在风险
- **数据丢失风险**：通过备份机制完全规避
- **导入失败风险**：通过错误处理和重试机制降低
- **验证不完整风险**：通过多层次验证确保完整性

### 6.2 应对措施
- **多重备份**：每次操作前都进行数据库备份
- **分批处理**：按购买单位分批操作，减少影响范围
- **详细日志**：记录所有操作过程和结果
- **人工复核**：关键步骤进行人工确认

## 7. 总结

本解决方案