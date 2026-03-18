#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="客户产品管理系统 - 批量版",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面标题
st.title("🏢 客户产品管理系统 - 批量版")
st.markdown("基于发货单目录中17个Excel文件创建的统一客户产品数据库")

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect('customer_products_unified.db')

def load_data():
    """加载数据库数据"""
    conn = get_db_connection()
    
    # 加载客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    
    # 加载订单信息
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    
    # 加载产品信息
    products = pd.read_sql_query("SELECT * FROM products", conn)
    
    conn.close()
    
    return customers, orders, products

# 侧边栏
st.sidebar.title("📋 导航菜单")
page = st.sidebar.selectbox(
    "选择功能",
    ["🏠 概览仪表板", "👥 客户管理", "📦 产品管理", "📊 数据统计", "🔍 数据搜索", "📁 文件管理"]
)

# 加载数据
customers, orders, products = load_data()

if page == "🏠 概览仪表板":
    st.header("📊 数据概览仪表板")
    
    # 关键指标
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("客户数量", len(customers))
    with col2:
        st.metric("订单数量", len(orders))
    with col3:
        st.metric("产品种类", len(products))
    with col4:
        total_amount = products['金额'].sum()
        st.metric("总金额", f"¥{total_amount:,.0f}")
    with col5:
        total_weight = products['数量_KG'].sum()
        st.metric("总重量", f"{total_weight:,.0f} KG")
    
    # 客户分布
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📈 客户产品分布")
        if not products.empty:
            customer_counts = products.groupby('客户ID').size()
            customer_names = customers.set_index('customer_id')['客户名称']
            fig = px.bar(
                x=customer_names[customer_counts.index], 
                y=customer_counts.values,
                title="各客户产品数量",
                labels={'x': '客户', 'y': '产品种类数'}
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 客户金额分布")
        if not products.empty:
            customer_amounts = products.groupby('客户ID')['金额'].sum()
            fig = px.pie(
                values=customer_amounts.values,
                names=customer_names[customer_amounts.index],
                title="各客户金额占比"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 文件处理状态
    st.subheader("📁 文件处理状态")
    file_stats = customers.groupby('文件名').size()
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**处理状态:**")
        for file_name, count in file_stats.items():
            st.write(f"✅ {file_name}: {count} 个客户")
    
    with col2:
        if not products.empty:
            source_stats = products.groupby('来源').size()
            st.write("**产品来源:**")
            for source, count in source_stats.items():
                st.write(f"📊 {source}: {count} 种产品")

elif page == "👥 客户管理":
    st.header("👥 客户信息管理")
    
    # 客户列表
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 客户筛选
        selected_customer = st.selectbox(
            "选择客户",
            ['全部'] + customers['客户名称'].tolist()
        )
        
        if selected_customer == '全部':
            display_customers = customers
        else:
            display_customers = customers[customers['客户名称'] == selected_customer]
        
        # 显示客户信息
        st.subheader(f"📋 客户信息 ({len(display_customers)} 个)")
        for _, customer in display_customers.iterrows():
            with st.expander(f"🏢 {customer['客户名称']}", expanded=True):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write(f"**客户名称:** {customer['客户名称']}")
                    st.write(f"**联系人:** {customer['联系人']}")
                    st.write(f"**电话:** {customer.get('电话', 'N/A')}")
                    st.write(f"**地址:** {customer.get('地址', 'N/A')}")
                
                with col_b:
                    st.write(f"**供应商:** {customer['供应商名称']}")
                    st.write(f"**供应商电话:** {customer['供应商电话']}")
                    st.write(f"**文件名:** {customer['文件名']}")
                    st.write(f"**创建时间:** {customer['创建时间']}")
    
    with col2:
        st.subheader("📊 客户统计")
        # 客户相关产品统计
        customer_products = products.groupby('客户ID').agg({
            '产品型号': 'count',
            '金额': 'sum',
            '数量_KG': 'sum'
        }).rename(columns={'产品型号': '产品种类数'})
        
        customer_products.index = customers.set_index('customer_id')['客户名称']
        st.dataframe(customer_products, use_container_width=True)

elif page == "📦 产品管理":
    st.header("📦 产品信息管理")
    
    # 产品筛选
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 按客户筛选
        selected_customer = st.selectbox(
            "客户",
            ['全部'] + customers['客户名称'].tolist()
        )
    
    with col2:
        # 按产品型号筛选
        models = ['全部'] + sorted(products['产品型号'].unique().tolist())
        selected_model = st.selectbox("产品型号", models)
    
    with col3:
        # 按来源筛选
        sources = ['全部'] + sorted(products['来源'].unique().tolist())
        selected_source = st.selectbox("数据来源", sources)
    
    with col4:
        # 按单价范围筛选
        min_price, max_price = st.slider(
            "单价范围",
            float(products['单价'].min()),
            float(products['单价'].max()),
            (float(products['单价'].min()), float(products['单价'].max()))
        )
    
    # 应用筛选
    filtered_products = products.copy()
    
    if selected_customer != '全部':
        customer_id = customers[customers['客户名称'] == selected_customer]['customer_id'].iloc[0]
        filtered_products = filtered_products[filtered_products['客户ID'] == customer_id]
    
    if selected_model != '全部':
        filtered_products = filtered_products[filtered_products['产品型号'] == selected_model]
    
    if selected_source != '全部':
        filtered_products = filtered_products[filtered_products['来源'] == selected_source]
    
    filtered_products = filtered_products[
        (filtered_products['单价'] >= min_price) & 
        (filtered_products['单价'] <= max_price)
    ]
    
    # 显示筛选后的产品
    st.subheader(f"📋 产品列表 (共{len(filtered_products)}种)")
    
    # 选择显示的列
    display_columns = st.multiselect(
        "选择显示的列",
        options=filtered_products.columns.tolist(),
        default=['产品型号', '产品名称', '规格_KG', '数量_件', '单价', '金额', '来源']
    )
    
    if display_columns:
        st.dataframe(
            filtered_products[display_columns],
            use_container_width=True,
            height=400
        )
    
    # 产品统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("产品种类数", len(filtered_products))
    with col2:
        st.metric("总数量(件)", f"{filtered_products['数量_件'].sum():.0f}")
    with col3:
        st.metric("总金额", f"¥{filtered_products['金额'].sum():,.2f}")
    with col4:
        st.metric("总重量(KG)", f"{filtered_products['数量_KG'].sum():,.2f}")

elif page == "📊 数据统计":
    st.header("📊 详细数据统计")
    
    # 总体统计
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("客户总数", len(customers))
    with col2:
        st.metric("产品种类", len(products))
    with col3:
        st.metric("总规格(KG)", f"{products['规格_KG'].sum():,.0f}")
    with col4:
        st.metric("总重量(KG)", f"{products['数量_KG'].sum():,.0f}")
    with col5:
        st.metric("总金额", f"¥{products['金额'].sum():,.0f}")
    
    # 数据可视化
    st.subheader("📈 数据可视化分析")
    
    # 客户产品分布
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**客户产品数量分布**")
        customer_counts = products.groupby('客户ID').size()
        customer_names = customers.set_index('customer_id')['客户名称']
        fig = px.bar(
            x=customer_names[customer_counts.index], 
            y=customer_counts.values,
            title="各客户产品数量",
            labels={'x': '客户', 'y': '产品种类数'}
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**产品规格分布**")
        fig = px.histogram(
            products, 
            x='规格_KG', 
            nbins=20,
            title="产品规格分布",
            labels={'规格_KG': '规格 (KG/桶)', 'count': '产品数量'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 按来源统计
    st.subheader("📊 按数据来源统计")
    source_stats = products.groupby('来源').agg({
        '产品型号': 'count',
        '数量_件': 'sum',
        '金额': 'sum'
    }).rename(columns={'产品型号': '产品种类数'})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**来源统计表**")
        st.dataframe(source_stats, use_container_width=True)
    
    with col2:
        st.write("**来源分布图**")
        fig = px.pie(
            source_stats.reset_index(), 
            values='产品种类数', 
            names='来源',
            title="产品种类数按来源分布"
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "🔍 数据搜索":
    st.header("🔍 数据搜索功能")
    
    # 搜索选项
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input("搜索产品名称或型号", "")
    
    with col2:
        search_type = st.selectbox("搜索类型", ["模糊搜索", "精确匹配"])
    
    # 执行搜索
    if search_term:
        if search_type == "模糊搜索":
            search_results = products[
                products['产品型号'].str.contains(search_term, case=False, na=False) |
                products['产品名称'].str.contains(search_term, case=False, na=False)
            ]
        else:
            search_results = products[
                (products['产品型号'] == search_term) |
                (products['产品名称'] == search_term)
            ]
        
        st.subheader(f"🔍 搜索结果 (共{len(search_results)}条)")
        
        if not search_results.empty:
            # 显示搜索结果
            display_cols = st.multiselect(
                "选择显示列",
                options=search_results.columns.tolist(),
                default=['产品型号', '产品名称', '规格_KG', '单价', '金额', '来源']
            )
            
            if display_cols:
                st.dataframe(
                    search_results[display_cols],
                    use_container_width=True,
                    height=300
                )
        else:
            st.warning("未找到匹配的结果")
    
    # 高级筛选
    st.subheader("🎯 高级筛选")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        price_range = st.slider(
            "金额范围",
            float(products['金额'].min()),
            float(products['金额'].max()),
            (float(products['金额'].min()), float(products['金额'].max()))
        )
    
    with col2:
        spec_range = st.slider(
            "规格范围",
            float(products['规格_KG'].min()),
            float(products['规格_KG'].max()),
            (float(products['规格_KG'].min()), float(products['规格_KG'].max()))
        )
    
    with col3:
        weight_range = st.slider(
            "重量范围",
            float(products['数量_KG'].min()),
            float(products['数量_KG'].max()),
            (float(products['数量_KG'].min()), float(products['数量_KG'].max()))
        )
    
    # 应用高级筛选
    advanced_filtered = products[
        (products['金额'] >= price_range[0]) & 
        (products['金额'] <= price_range[1]) &
        (products['规格_KG'] >= spec_range[0]) & 
        (products['规格_KG'] <= spec_range[1]) &
        (products['数量_KG'] >= weight_range[0]) & 
        (products['数量_KG'] <= weight_range[1])
    ]
    
    st.subheader(f"🎯 筛选结果 (共{len(advanced_filtered)}条)")
    
    if not advanced_filtered.empty:
        st.dataframe(
            advanced_filtered[['产品型号', '产品名称', '规格_KG', '数量_KG', '单价', '金额', '来源']],
            use_container_width=True,
            height=300
        )
        
        # 导出功能
        if st.button("📥 导出筛选结果"):
            csv = advanced_filtered.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 下载CSV",
                data=csv,
                file_name=f'批量产品筛选结果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )

elif page == "📁 文件管理":
    st.header("📁 文件处理状态")
    
    # 文件处理统计
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 文件处理概览")
        file_stats = customers.groupby('文件名').size()
        total_files = len(file_stats)
        total_customers = file_stats.sum()
        
        st.metric("总文件数", total_files)
        st.metric("总客户数", total_customers)
        st.metric("平均每文件客户数", f"{total_customers/total_files:.1f}")
        
        # 显示文件状态
        st.write("**文件处理状态:**")
        for file_name, count in file_stats.items():
            st.write(f"✅ {file_name}: {count} 个客户")
    
    with col2:
        st.subheader("📈 文件产品分布")
        file_products = products.groupby('来源').size()
        fig = px.bar(
            x=[source.split('-')[0] for source in file_products.index],
            y=file_products.values,
            title="各文件产品数量",
            labels={'x': '文件名', 'y': '产品种类数'}
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    # 数据质量检查
    st.subheader("🔍 数据质量检查")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        empty_models = len(products[products['产品型号'] == ''])
        st.metric("空产品型号", empty_models)
    
    with col2:
        empty_names = len(products[products['产品名称'] == ''])
        st.metric("空产品名称", empty_names)
    
    with col3:
        zero_amounts = len(products[products['金额'] == 0])
        st.metric("零金额记录", zero_amounts)
    
    # 数据完整性报告
    st.subheader("📋 数据完整性报告")
    
    completeness = {
        '字段': ['产品型号', '产品名称', '规格_KG', '数量_件', '数量_KG', '单价', '金额'],
        '完整率(%)': [
            (len(products[products['产品型号'] != '']) / len(products) * 100),
            (len(products[products['产品名称'] != '']) / len(products) * 100),
            (len(products[products['规格_KG'] != 0]) / len(products) * 100),
            (len(products[products['数量_件'] != 0]) / len(products) * 100),
            (len(products[products['数量_KG'] != 0]) / len(products) * 100),
            (len(products[products['单价'] != 0]) / len(products) * 100),
            (len(products[products['金额'] != 0]) / len(products) * 100)
        ]
    }
    
    completeness_df = pd.DataFrame(completeness)
    st.dataframe(completeness_df, use_container_width=True)

# 页脚
st.markdown("---")
st.markdown(
    "🏢 **客户产品管理系统 - 批量版** | "
    "📁 17个Excel文件 | "
    "👥 8个客户 | "
    "📦 512种产品 | "
    "🕒 创建时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)