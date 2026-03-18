#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析不同购买单位之间的产品混淆情况
"""

import pandas as pd
import json
from datetime import datetime


def analyze_unit_confusion():
    """
    分析不同购买单位之间的产品混淆情况
    
    Returns:
        dict: 分析结果
    """
    print("=== 购买单位产品混淆分析 ===")
    
    # 读取Excel数据
    excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    
    print(f"Excel数据总行数: {len(df)}")
    print(f"购买单位数量: {df['购买单位'].nunique()}")
    print()
    
    # 1. 分析相同产品型号在不同单位中的使用情况
    print("1. 相同产品型号在不同购买单位中的使用情况:")
    
    # 按产品型号分组，统计使用该型号的购买单位数
    model_unit_counts = df.groupby('产品型号')['购买单位'].nunique().reset_index()
    model_unit_counts.columns = ['产品型号', '使用单位数']
    
    # 找出被多个单位使用的产品型号
    multi_unit_models = model_unit_counts[model_unit_counts['使用单位数'] > 1]
    print(f"被多个购买单位使用的产品型号数: {len(multi_unit_models)}")
    
    if not multi_unit_models.empty:
        print("被多个购买单位使用的产品型号 (前20个):")
        # 按使用单位数排序
        sorted_multi_unit_models = multi_unit_models.sort_values('使用单位数', ascending=False)
        
        for idx, row in sorted_multi_unit_models.head(20).iterrows():
            # 找出使用该型号的具体单位
            units_using_model = df[df['产品型号'] == row['产品型号']]['购买单位'].unique()
            print(f"  型号: {row['产品型号']}, 使用单位数: {row['使用单位数']}, 单位: {', '.join(units_using_model)}")
    print()
    
    # 2. 分析相同产品名称在不同单位中的使用情况
    print("2. 相同产品名称在不同购买单位中的使用情况:")
    
    name_unit_counts = df.groupby('产品名称')['购买单位'].nunique().reset_index()
    name_unit_counts.columns = ['产品名称', '使用单位数']
    
    multi_unit_names = name_unit_counts[name_unit_counts['使用单位数'] > 1]
    print(f"被多个购买单位使用的产品名称数: {len(multi_unit_names)}")
    
    if not multi_unit_names.empty:
        print("被多个购买单位使用的产品名称 (前20个):")
        sorted_multi_unit_names = multi_unit_names.sort_values('使用单位数', ascending=False)
        
        for idx, row in sorted_multi_unit_names.head(20).iterrows():
            units_using_name = df[df['产品名称'] == row['产品名称']]['购买单位'].unique()
            print(f"  名称: {row['产品名称']}, 使用单位数: {row['使用单位数']}, 单位: {', '.join(units_using_name)}")
    print()
    
    # 3. 分析价格差异
    print("3. 相同产品型号在不同单位中的价格差异:")
    
    # 计算每个产品型号在不同单位中的价格统计
    model_price_stats = df.groupby('产品型号').agg({
        '单价': ['mean', 'min', 'max', 'std'],
        '购买单位': 'nunique'
    }).reset_index()
    
    model_price_stats.columns = ['产品型号', '平均价格', '最低价格', '最高价格', '价格标准差', '使用单位数']
    
    # 找出有价格差异的产品型号
    model_price_stats['价格差异'] = model_price_stats['最高价格'] - model_price_stats['最低价格']
    price_variation_models = model_price_stats[model_price_stats['价格差异'] > 0]
    
    print(f"存在价格差异的产品型号数: {len(price_variation_models)}")
    
    if not price_variation_models.empty:
        print("价格差异较大的产品型号 (前20个):")
        sorted_price_variation = price_variation_models.sort_values('价格差异', ascending=False)
        
        for idx, row in sorted_price_variation.head(20).iterrows():
            # 获取该型号在不同单位的具体价格
            unit_prices = df[df['产品型号'] == row['产品型号']][['购买单位', '单价']].drop_duplicates()
            price_info = [f"{unit}: {price}" for unit, price in zip(unit_prices['购买单位'], unit_prices['单价'])]
            print(f"  型号: {row['产品型号']}, 价格差异: {row['价格差异']:.2f}, 价格范围: {row['最低价格']:.2f}-{row['最高价格']:.2f}, 单位价格: {', '.join(price_info)}")
    print()
    
    # 4. 分析每个购买单位的产品特征
    print("4. 各购买单位的产品特征分析:")
    
    unit_analysis = []
    for unit in df['购买单位'].unique():
        unit_data = df[df['购买单位'] == unit]
        
        # 转换产品型号为字符串
        unit_data['产品型号'] = unit_data['产品型号'].astype(str)
        
        analysis = {
            '购买单位': unit,
            '产品总数': len(unit_data),
            '唯一型号数': unit_data['产品型号'].nunique(),
            '唯一产品名称数': unit_data['产品名称'].nunique(),
            '平均价格': unit_data['单价'].mean(),
            '价格范围': [unit_data['单价'].min(), unit_data['单价'].max()],
            '主要产品型号': unit_data['产品型号'].value_counts().head(5).index.tolist(),
            '主要产品名称': unit_data['产品名称'].value_counts().head(5).index.tolist()
        }
        
        unit_analysis.append(analysis)
        
        print(f"购买单位: {unit}")
        print(f"  产品总数: {analysis['产品总数']}")
        print(f"  唯一型号数: {analysis['唯一型号数']}")
        print(f"  唯一产品名称数: {analysis['唯一产品名称数']}")
        print(f"  平均价格: {analysis['平均价格']:.2f}")
        print(f"  价格范围: {analysis['价格范围'][0]:.2f}-{analysis['价格范围'][1]:.2f}")
        print(f"  主要产品型号: {', '.join(analysis['主要产品型号'])}")
        print(f"  主要产品名称: {', '.join(analysis['主要产品名称'])}")
        print()
    
    # 5. 生成综合分析结果
    analysis_result = {
        'basic_stats': {
            'total_rows': len(df),
            'unique_units': df['购买单位'].nunique(),
            'unique_models': df['产品型号'].nunique(),
            'unique_names': df['产品名称'].nunique()
        },
        'confusion_analysis': {
            'multi_unit_models_count': len(multi_unit_models),
            'multi_unit_names_count': len(multi_unit_names),
            'price_variation_models_count': len(price_variation_models)
        },
        'detailed_analysis': {
            'multi_unit_models': multi_unit_models.to_dict('records'),
            'price_variation_models': price_variation_models.to_dict('records')
        },
        'unit_analysis': unit_analysis
    }
    
    return analysis_result


def main():
    """
    主函数
    """
    # 执行分析
    analysis_result = analyze_unit_confusion()
    
    # 保存分析结果
    output_file = f"unit_confusion_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 购买单位混淆分析结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
