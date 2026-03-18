#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Sheet2工作表，这是真正的产品列表
"""

import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

excel_path = "尹玉华1 - 副本.xlsx"

def analyze_sheet2():
    """分析Sheet2工作表"""
    try:
        # 读取Sheet2工作表
        df = pd.read_excel(excel_path, sheet_name='Sheet2')
        logger.info(f"Sheet2 工作表行数: {len(df)}")
        logger.info(f"Sheet2 工作表列名: {df.columns.tolist()}")
        
        # 显示前10行数据
        logger.info("Sheet2 前10行数据:")
        print(df.head(10))
        
        # 查找真正的表头行（包含产品编号的列）
        header_row = None
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            if any('编号' in str(cell) for cell in row if pd.notna(cell)):
                header_row = i
                logger.info(f"找到表头行在第{i+1}行")
                break
        
        if header_row is not None:
            # 使用找到的行作为表头重新读取
            df = pd.read_excel(excel_path, sheet_name='Sheet2', header=header_row)
            logger.info(f"重新读取后的列名: {df.columns.tolist()}")
            
            # 显示重新读取后的前10行
            logger.info("重新读取后的前10行数据:")
            print(df.head(10))
            
            # 查找产品编号和产品名称列
            product_code_col = None
            product_name_col = None
            spec_col = None
            internal_price_col = None
            external_price_col = None
            
            for col in df.columns:
                col_str = str(col)
                if '编号' in col_str or '产品编号' in col_str:
                    product_code_col = col
                elif '名称' in col_str or '产品名称' in col_str:
                    product_name_col = col
                elif '规格' in col_str:
                    spec_col = col
                elif '内' in col_str or '内部' in col_str:
                    internal_price_col = col
                elif '外' in col_str or '外部' in col_str:
                    external_price_col = col
            
            logger.info(f"产品编号列: {product_code_col}")
            logger.info(f"产品名称列: {product_name_col}")
            logger.info(f"规格列: {spec_col}")
            logger.info(f"内单价列: {internal_price_col}")
            logger.info(f"外单价列: {external_price_col}")
            
            # 提取产品数据
            if product_code_col and product_name_col:
                # 过滤掉表头行和空值
                product_data = df[[product_code_col, product_name_col]].dropna()
                
                # 过滤掉无效的产品编号
                valid_products = []
                for _, row in product_data.iterrows():
                    code = str(row[product_code_col]).strip()
                    name = str(row[product_name_col]).strip()
                    
                    # 跳过明显的非产品行
                    if code in ['编号', 'nan', ''] or name in ['编号', 'nan', '', '产品名称']:
                        continue
                    
                    # 确保编号不为空且不是纯文本
                    if code and code != 'nan' and len(code) > 0 and not code.isalpha():
                        valid_products.append((code, name))
                
                logger.info(f"找到 {len(valid_products)} 个有效产品")
                
                # 显示所有有效产品
                logger.info("所有有效产品:")
                for code, name in valid_products:
                    logger.info(f"  - {code}: {name}")
                
                return valid_products
        
        return []
        
    except Exception as e:
        logger.error(f"分析Sheet2失败: {e}")
        return []

def main():
    """主函数"""
    print("=== 分析Sheet2工作表 ===")
    products = analyze_sheet2()
    print(f"\nSheet2中真正产品数量: {len(products)}")

if __name__ == "__main__":
    main()
