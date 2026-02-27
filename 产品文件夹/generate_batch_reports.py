#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
import json
from datetime import datetime

def generate_batch_html_report():
    """生成批量处理后的HTML报告"""
    print("=== 生成批量处理HTML报告 ===")
    
    # 连接统一数据库
    conn = sqlite3.connect('customer_products_unified.db')
    
    # 加载数据
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    products = pd.read_sql_query("SELECT * FROM products", conn)
    
    conn.close()
    
    # 生成HTML内容
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>客户产品管理系统 - 批量版报告</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .metric h3 {{
                margin: 0;
                font-size: 2em;
            }}
            .metric p {{
                margin: 5px 0 0 0;
                opacity: 0.9;
            }}
            .section {{
                margin-bottom: 40px;
            }}
            .section h2 {{
                color: #34495e;
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-bottom: 20px;
            }}
            .customer-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .customer-card {{
                background-color: #ecf0f1;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }}
            .table-container {{
                overflow-x: auto;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #e8f4f8;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #7f8c8d;
            }}
            .file-status {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            .file-card {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }}
            .success {{ color: #28a745; }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 客户产品管理系统 - 批量版</h1>
                <p>📊 基于发货单目录中17个Excel文件的统一客户产品数据库</p>
                <p>🕒 生成时间: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>{len(customers)}</h3>
                    <p>客户数量</p>
                </div>
                <div class="metric">
                    <h3>{len(orders)}</h3>
                    <p>订单数量</p>
                </div>
                <div class="metric">
                    <h3>{len(products)}</h3>
                    <p>产品种类</p>
                </div>
                <div class="metric">
                    <h3>¥{products['金额'].sum():,.0f}</h3>
                    <p>总金额</p>
                </div>
                <div class="metric">
                    <h3>{products['数量_KG'].sum():,.0f}</h3>
                    <p>总重量(KG)</p>
                </div>
            </div>
    """
    
    # 文件处理状态
    html_content += """
            <div class="section">
                <h2>📁 文件处理状态</h2>
                <div class="file-status">
    """
    
    file_stats = customers.groupby('文件名').size()
    for file_name, count in file_stats.items():
        html_content += f"""
                    <div class="file-card">
                        <h4>✅ {file_name}</h4>
                        <p><strong>客户数:</strong> {count}</p>
                        <p><strong>状态:</strong> <span class="success">处理成功</span></p>
                    </div>
        """
    
    html_content += """
                </div>
            </div>
    """
    
    # 客户信息部分
    if not customers.empty:
        html_content += """
            <div class="section">
                <h2>👥 客户信息汇总</h2>
                <div class="customer-grid">
        """
        for _, customer in customers.iterrows():
            # 获取该客户的产品统计
            customer_products = products[products['客户ID'] == customer['customer_id']]
            product_count = len(customer_products)
            total_amount = customer_products['金额'].sum()
            total_weight = customer_products['数量_KG'].sum()
            
            html_content += f"""
                    <div class="customer-card">
                        <h3>🏢 {customer['客户名称']}</h3>
                        <p><strong>联系人:</strong> {customer.get('联系人', 'N/A')}</p>
                        <p><strong>电话:</strong> {customer.get('电话', 'N/A')}</p>
                        <p><strong>供应商:</strong> {customer.get('供应商名称', 'N/A')}</p>
                        <p><strong>供应商电话:</strong> {customer.get('供应商电话', 'N/A')}</p>
                        <p><strong>产品种类:</strong> {product_count}</p>
                        <p><strong>总金额:</strong> ¥{total_amount:,.2f}</p>
                        <p><strong>总重量:</strong> {total_weight:,.2f} KG</p>
                        <p><strong>来源文件:</strong> {customer.get('文件名', 'N/A')}</p>
                        <p><strong>创建时间:</strong> {customer.get('创建时间', 'N/A')}</p>
                    </div>
            """
        html_content += """
                </div>
            </div>
        """
    
    # 产品信息部分
    html_content += """
        <div class="section">
            <h2>📦 产品信息汇总 (前50个)</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>产品型号</th>
                            <th>产品名称</th>
                            <th>规格(KG/桶)</th>
                            <th>数量(件)</th>
                            <th>重量(KG)</th>
                            <th>单价(元)</th>
                            <th>金额(元)</th>
                            <th>客户</th>
                            <th>数据来源</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # 显示前50个产品
    for i, (_, product) in enumerate(products.head(50).iterrows(), 1):
        # 获取客户名称
        customer_name = customers[customers['customer_id'] == product['客户ID']]['客户名称'].iloc[0] if len(customers[customers['customer_id'] == product['客户ID']]) > 0 else 'N/A'
        
        html_content += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{product.get('产品型号', 'N/A')}</td>
                            <td>{product.get('产品名称', 'N/A')}</td>
                            <td>{product.get('规格_KG', 0):.1f}</td>
                            <td>{product.get('数量_件', 0):.0f}</td>
                            <td>{product.get('数量_KG', 0):.1f}</td>
                            <td>{product.get('单价', 0):.2f}</td>
                            <td>{product.get('金额', 0):.2f}</td>
                            <td>{customer_name}</td>
                            <td>{product.get('来源', 'N/A')}</td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 详细统计 -->
        <div class="section">
            <h2>📊 详细统计汇总</h2>
            <div class="stats-grid">
                <div class="metric">
                    <h3>{products['数量_件'].sum():.0f}</h3>
                    <p>总数量(件)</p>
                </div>
                <div class="metric">
                    <h3>{products['规格_KG'].sum():,.0f}</h3>
                    <p>总规格(KG/桶)</p>
                </div>
                <div class="metric">
                    <h3>{products['数量_KG'].sum():,.0f}</h3>
                    <p>总重量(KG)</p>
                </div>
                <div class="metric">
                    <h3>{products['单价'].sum():,.0f}</h3>
                    <p>单价总计(元)</p>
                </div>
            </div>
        </div>
        
        <!-- 按客户统计 -->
        <div class="section">
            <h2>📈 按客户统计</h2>
    """
    
    # 按客户统计
    customer_stats = products.groupby('客户ID').agg({
        '产品型号': 'count',
        '数量_件': 'sum',
        '数量_KG': 'sum',
        '金额': 'sum'
    }).rename(columns={'产品型号': '产品种类数'})
    
    customer_names = customers.set_index('customer_id')['客户名称']
    customer_stats.index = customer_names[customer_stats.index]
    
    html_content += """
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>客户名称</th>
                            <th>产品种类数</th>
                            <th>总数量(件)</th>
                            <th>总重量(KG)</th>
                            <th>总金额(元)</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for customer_name, stats in customer_stats.iterrows():
        html_content += f"""
                        <tr>
                            <td>{customer_name}</td>
                            <td>{stats['产品种类数']}</td>
                            <td>{stats['数量_件']:.0f}</td>
                            <td>{stats['数量_KG']:.1f}</td>
                            <td>{stats['金额']:.2f}</td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 按文件统计 -->
        <div class="section">
            <h2>📁 按文件统计</h2>
    """
    
    # 按来源统计
    source_stats = products.groupby('来源').agg({
        '产品型号': 'count',
        '数量_件': 'sum',
        '金额': 'sum'
    }).rename(columns={'产品型号': '产品种类数'})
    
    html_content += """
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>文件来源</th>
                            <th>产品种类数</th>
                            <th>总数量(件)</th>
                            <th>总金额(元)</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for source, stats in source_stats.iterrows():
        html_content += f"""
                        <tr>
                            <td>{source}</td>
                            <td>{stats['产品种类数']}</td>
                            <td>{stats['数量_件']:.0f}</td>
                            <td>{stats['金额']:.2f}</td>
                        </tr>
        """
    
    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>🏢 <strong>客户产品管理系统 - 批量版</strong> | 📁 17个Excel文件 | 👥 {len(customers)}个客户 | 📦 {len(products)}种产品</p>
            <p>📊 数据库文件: customer_products_unified.db | 🕒 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </body>
    </html>
    """
    
    # 保存HTML文件
    with open('customer_products_batch_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ 批量处理HTML报告已生成: customer_products_batch_report.html")

def generate_batch_csv_exports():
    """生成批量处理的CSV导出文件"""
    print("\n=== 生成批量处理CSV导出文件 ===")
    
    conn = sqlite3.connect('customer_products_unified.db')
    
    # 导出客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    customers.to_csv('customers_batch_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出产品信息
    products = pd.read_sql_query("SELECT * FROM products", conn)
    products.to_csv('products_batch_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出订单信息
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    orders.to_csv('orders_batch_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出文件统计
    file_stats = customers.groupby('文件名').size().reset_index()
    file_stats.columns = ['文件名', '客户数量']
    file_stats.to_csv('file_stats_batch.csv', index=False, encoding='utf-8-sig')
    
    # 导出客户统计
    customer_stats = products.groupby('客户ID').agg({
        '产品型号': 'count',
        '数量_件': 'sum',
        '数量_KG': 'sum',
        '金额': 'sum'
    }).rename(columns={'产品型号': '产品种类数'})
    
    customer_names = customers.set_index('customer_id')['客户名称']
    customer_stats.index = customer_names[customer_stats.index]
    customer_stats.reset_index(inplace=True)
    customer_stats.rename(columns={'index': '客户名称'}, inplace=True)
    customer_stats.to_csv('customer_stats_batch.csv', index=False, encoding='utf-8-sig')
    
    conn.close()
    
    print("✅ 批量处理CSV导出文件已生成:")
    print("  - customers_batch_export.csv")
    print("  - products_batch_export.csv") 
    print("  - orders_batch_export.csv")
    print("  - file_stats_batch.csv")
    print("  - customer_stats_batch.csv")

if __name__ == "__main__":
    print("=== 生成批量处理报告和导出文件 ===")
    
    # 生成批量处理HTML报告
    generate_batch_html_report()
    
    # 生成批量处理CSV导出
    generate_batch_csv_exports()
    
    print("\n=== 完成 ===")
    print("🌐 批量版Web界面: http://localhost:8501 (Streamlit)")
    print("📄 批量版HTML报告: customer_products_batch_report.html")
    print("📊 批量版CSV导出: customers_batch_export.csv, products_batch_export.csv, orders_batch_export.csv")