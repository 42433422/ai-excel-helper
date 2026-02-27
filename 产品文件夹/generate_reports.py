#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
import json
from datetime import datetime

def generate_html_report():
    """生成HTML报告"""
    print("=== 生成HTML数据报告 ===")
    
    # 连接数据库
    conn = sqlite3.connect('customer_products_final.db')
    
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
        <title>客户产品管理系统 - 数据报告</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
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
            .customer-info {{
                background-color: #ecf0f1;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 客户产品管理系统</h1>
                <p>📊 基于Excel数据创建的以客户为核心的产品数据库</p>
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
            </div>
    """
    
    # 客户信息部分
    if not customers.empty:
        html_content += """
            <div class="section">
                <h2>👥 客户信息</h2>
                <div class="customer-info">
        """
        for _, customer in customers.iterrows():
            html_content += f"""
                    <h3>🏢 {customer['客户名称']}</h3>
                    <p><strong>联系人:</strong> {customer.get('联系人', 'N/A')}</p>
                    <p><strong>电话:</strong> {customer.get('电话', 'N/A')}</p>
                    <p><strong>供应商:</strong> {customer.get('供应商名称', 'N/A')}</p>
                    <p><strong>供应商电话:</strong> {customer.get('供应商电话', 'N/A')}</p>
                    <p><strong>创建时间:</strong> {customer.get('创建时间', 'N/A')}</p>
            """
        html_content += """
                </div>
            </div>
        """
    
    # 订单信息部分
    if not orders.empty:
        html_content += """
            <div class="section">
                <h2>📋 订单信息</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>订单编号</th>
                                <th>订单日期</th>
                                <th>订单状态</th>
                                <th>创建时间</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for _, order in orders.iterrows():
            html_content += f"""
                            <tr>
                                <td>{order.get('订单编号', 'N/A')}</td>
                                <td>{order.get('订单日期', 'N/A')}</td>
                                <td>{order.get('订单状态', 'N/A')}</td>
                                <td>{order.get('创建时间', 'N/A')}</td>
                            </tr>
            """
        html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        """
    
    # 产品信息部分
    html_content += """
        <div class="section">
            <h2>📦 产品信息 (前20个)</h2>
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
                            <th>数据来源</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # 显示前20个产品
    for i, (_, product) in enumerate(products.head(20).iterrows(), 1):
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
                            <td>{product.get('来源', 'N/A')}</td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 数据统计 -->
        <div class="section">
            <h2>📊 数据统计汇总</h2>
            <div class="summary">
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
        
        <!-- 按来源统计 -->
        <div class="section">
            <h2>📈 按数据来源统计</h2>
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
                            <th>数据来源</th>
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
            <p>🏢 <strong>客户产品管理系统</strong> | 📅 基于Excel数据 | 🕒 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>📊 数据库文件: customer_products_final.db | 📋 产品总数: {len(products)} 种</p>
        </div>
    </body>
    </html>
    """
    
    # 保存HTML文件
    with open('customer_products_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ HTML报告已生成: customer_products_report.html")

def generate_csv_exports():
    """生成CSV导出文件"""
    print("\n=== 生成CSV导出文件 ===")
    
    conn = sqlite3.connect('customer_products_final.db')
    
    # 导出客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    customers.to_csv('customers_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出产品信息
    products = pd.read_sql_query("SELECT * FROM products", conn)
    products.to_csv('products_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出订单信息
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    orders.to_csv('orders_export.csv', index=False, encoding='utf-8-sig')
    
    conn.close()
    
    print("✅ CSV导出文件已生成:")
    print("  - customers_export.csv")
    print("  - products_export.csv") 
    print("  - orders_export.csv")

if __name__ == "__main__":
    print("=== 生成前端报告和导出文件 ===")
    
    # 生成HTML报告
    generate_html_report()
    
    # 生成CSV导出
    generate_csv_exports()
    
    print("\n=== 完成 ===")
    print("🌐 Web界面: http://localhost:8501 (Streamlit)")
    print("📄 HTML报告: customer_products_report.html")
    print("📊 CSV导出: customers_export.csv, products_export.csv, orders_export.csv")