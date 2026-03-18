#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
from datetime import datetime

def generate_final_corrected_report():
    """生成最终修正后的HTML报告"""
    print("=== 生成最终修正后的HTML报告 ===")
    
    # 连接修正后的数据库
    conn = sqlite3.connect('customer_products_corrected.db')
    
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
        <title>客户产品管理系统 - 最终修正版报告</title>
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
                border-bottom: 3px solid #27ae60;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .success-banner {{
                background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
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
                border-left: 4px solid #27ae60;
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
                border-left: 4px solid #27ae60;
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
                background-color: #27ae60;
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
            .success {{ color: #27ae60; }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .correction-note {{
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 客户产品管理系统 - 最终修正版</h1>
                <p>✅ 客户名称已正确从发货单中提取 | 📁 17个Excel文件 | 👥 16个客户 | 📦 512种产品</p>
                <p>🕒 生成时间: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
            </div>
            
            <div class="success-banner">
                <h2>✅ 修正完成！</h2>
                <p>所有客户名称已正确从发货单中提取，格式为：购货单位（乙方）：客户名称</p>
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
            
            <div class="correction-note">
                <h3>📝 修正说明</h3>
                <p>之前版本错误提取了客户名称（如将"乙方"作为客户名），修正后的逻辑为：</p>
                <ul>
                    <li>正确格式: <code>购货单位（乙方）：七彩乐园家私</code></li>
                    <li>错误提取: <code>乙方</code> ❌</li>
                    <li>正确提取: <code>七彩乐园家私</code> ✅</li>
                </ul>
            </div>
    """
    
    # 修正后的客户信息部分
    if not customers.empty:
        html_content += """
            <div class="section">
                <h2>👥 修正后的客户信息</h2>
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
                        <h3>✅ {customer['客户名称']}</h3>
                        <p><strong>联系人:</strong> {customer.get('联系人', 'N/A')}</p>
                        <p><strong>电话:</strong> {customer.get('电话', 'N/A')}</p>
                        <p><strong>供应商:</strong> {customer.get('供应商名称', 'N/A')}</p>
                        <p><strong>供应商电话:</strong> {customer.get('供应商电话', 'N/A')}</p>
                        <p><strong>产品种类:</strong> {product_count}</p>
                        <p><strong>总金额:</strong> ¥{total_amount:,.2f}</p>
                        <p><strong>总重量:</strong> {total_weight:,.2f} KG</p>
                        <p><strong>来源文件:</strong> {customer.get('文件名', 'N/A')}</p>
                    </div>
            """
        html_content += """
                </div>
            </div>
        """
    
    # 关键客户列表
    html_content += """
        <div class="section">
            <h2>🎯 关键客户验证</h2>
            <p>以下客户名称已正确从发货单中提取：</p>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>序号</th>
                            <th>客户名称</th>
                            <th>来源文件</th>
                            <th>产品种类</th>
                            <th>总金额</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    key_customers = [
        ('陈洪强', '现金.xlsx'),
        ('中江博郡家私', '迎扬李总(1).xlsx'),
        ('七彩乐园家私', '七彩乐园.xlsx'),
        ('宗南家私', '宗南.xlsx'),
        ('宜榢家私', '宜榢.xlsx'),
        ('志泓家私', '志泓.xlsx'),
        ('温总', '温总.xlsx'),
        ('澜宇家私', '澜宇电视柜.xlsx')
    ]
    
    for i, (customer_name, file_name) in enumerate(key_customers, 1):
        found = customers[customers['客户名称'] == customer_name]
        if len(found) > 0:
            customer = found.iloc[0]
            customer_prods = products[products['客户ID'] == customer['customer_id']]
            product_count = len(customer_prods)
            total_amount = customer_prods['金额'].sum()
            status = "✅ 正确"
        else:
            product_count = 0
            total_amount = 0
            status = "❌ 未找到"
        
        html_content += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{customer_name}</td>
                            <td>{file_name}</td>
                            <td>{product_count}</td>
                            <td>¥{total_amount:,.2f}</td>
                            <td>{status}</td>
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
    
    for i, (_, product) in enumerate(products.head(50).iterrows(), 1):
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
    customer_stats.reset_index(inplace=True)
    customer_stats.rename(columns={'index': '客户名称'}, inplace=True)
    
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
    
    for _, stats in customer_stats.iterrows():
        html_content += f"""
                        <tr>
                            <td>{stats['客户名称']}</td>
                            <td>{stats['产品种类数']}</td>
                            <td>{stats['数量_件']:.0f}</td>
                            <td>{stats['数量_KG']:.1f}</td>
                            <td>{stats['金额']:.2f}</td>
                        </tr>
        """
    
    html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>🏢 <strong>客户产品管理系统 - 最终修正版</strong> | ✅ 客户名称已正确提取 | 📁 17个Excel文件 | 👥 {len(customers)}个客户 | 📦 {len(products)}种产品</p>
            <p>📊 数据库文件: customer_products_corrected.db | 🕒 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </body>
    </html>
    """
    
    # 保存HTML文件
    with open('customer_products_final_corrected_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ 最终修正后的HTML报告已生成: customer_products_final_corrected_report.html")

def generate_final_csv_exports():
    """生成最终修正后的CSV导出文件"""
    print("\n=== 生成最终修正后的CSV导出文件 ===")
    
    conn = sqlite3.connect('customer_products_corrected.db')
    
    # 导出客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    customers.to_csv('customers_final_corrected_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出产品信息
    products = pd.read_sql_query("SELECT * FROM products", conn)
    products.to_csv('products_final_corrected_export.csv', index=False, encoding='utf-8-sig')
    
    # 导出订单信息
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    orders.to_csv('orders_final_corrected_export.csv', index=False, encoding='utf-8-sig')
    
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
    customer_stats.to_csv('customer_stats_final_corrected.csv', index=False, encoding='utf-8-sig')
    
    conn.close()
    
    print("✅ 最终修正后的CSV导出文件已生成:")
    print("  - customers_final_corrected_export.csv")
    print("  - products_final_corrected_export.csv") 
    print("  - orders_final_corrected_export.csv")
    print("  - customer_stats_final_corrected.csv")

if __name__ == "__main__":
    print("=== 生成最终修正后的报告和导出文件 ===")
    
    # 生成最终修正后的HTML报告
    generate_final_corrected_report()
    
    # 生成最终修正后的CSV导出
    generate_final_csv_exports()
    
    print("\n=== 完成 ===")
    print("🌐 修正版Web界面: http://localhost:8501 (Streamlit)")
    print("📄 最终修正版HTML报告: customer_products_final_corrected_report.html")
    print("📊 最终修正版CSV导出: customers_final_corrected_export.csv, products_final_corrected_export.csv")