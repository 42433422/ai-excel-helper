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
    page_title="客户产品管理系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面标题
st.title("🏢 客户产品管理系统")
st.markdown("基于Excel数据创建的以客户为核心的产品数据库管理系统")

def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect('customer_products_final.db')

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
    ["🏠 概览仪表板", "👥 客户信息", "📦 产品管理", "📊 数据统计", "🔍 数据搜索"]
)

# 加载数据
customers, orders, products = load_data()

if page == "🏠 概览仪表板":
    st.header("📊 数据概览仪表板")
    
    # 关键指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("客户数量", len(customers))
    with col2:
        st.metric("订单数量", len(orders))
    with col3:
        st.metric("产品种类", len(products))
    with col4:
        total_amount = products['金额'].sum()
        st.metric("总金额", f"¥{total_amount:,.2f}")
    
    # 数据展示
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📈 产品数量分布")
        if not products.empty:
            fig = px.bar(
                products.head(10), 
                x='产品型号', 
                y='数量_件',
                title="Top 10 产品数量(件)",
                color='产品型号'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 产品金额分布")
        if not products.empty:
            fig = px.pie(
                products.head(10), 
                values='金额', 
                names='产品型号',
                title="Top 10 产品金额占比"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 最新产品展示
    st.subheader("🆕 最新产品记录")
    if not products.empty:
        # 按记录顺序排序显示最新5个
        latest_products = products.nlargest(5, '记录顺序')[
            ['产品型号', '产品名称', '规格_KG', '数量_件', '单价', '金额', '来源']
        ]
        st.dataframe(latest_products, use_container_width=True)

elif page == "👥 客户信息":
    st.header("👥 客户信息管理")
    
    if not customers.empty:
        for _, customer in customers.iterrows():
            with st.expander(f"🏢 {customer['客户名称']}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**客户名称:** {customer['客户名称']}")
                    st.write(f"**联系人:** {customer['联系人']}")
                    st.write(f"**电话:** {customer.get('电话', 'N/A')}")
                    st.write(f"**地址:** {customer.get('地址', 'N/A')}")
                
                with col2:
                    st.write(f"**供应商:** {customer['供应商名称']}")
                    st.write(f"**供应商电话:** {customer['供应商电话']}")
                    st.write(f"**创建时间:** {customer['创建时间']}")
                    st.write(f"**更新时间:** {customer['更新时间']}")
    
    # 显示订单信息
    if not orders.empty:
        st.subheader("📋 相关订单")
        orders_display = orders[['订单编号', '订单日期', '订单状态']]
        st.dataframe(orders_display, use_container_width=True)

elif page == "📦 产品管理":
    st.header("📦 产品信息管理")
    
    # 产品筛选
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 按产品型号筛选
        models = ['全部'] + sorted(products['产品型号'].unique().tolist())
        selected_model = st.selectbox("产品型号", models)
    
    with col2:
        # 按来源筛选
        sources = ['全部'] + sorted(products['来源'].unique().tolist())
        selected_source = st.selectbox("数据来源", sources)
    
    with col3:
        # 按单价范围筛选
        min_price, max_price = st.slider(
            "单价范围",
            float(products['单价'].min()),
            float(products['单价'].max()),
            (float(products['单价'].min()), float(products['单价'].max()))
        )
    
    # 应用筛选
    filtered_products = products.copy()
    
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
    st.subheader("📊 产品统计")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("产品种类数", len(filtered_products))
    with col2:
        st.metric("总数量(件)", f"{filtered_products['数量_件'].sum():.0f}")
    with col3:
        st.metric("总金额", f"¥{filtered_products['金额'].sum():,.2f}")

elif page == "📊 数据统计":
    st.header("📊 详细数据统计")
    
    # 总体统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("客户总数", len(customers))
    with col2:
        st.metric("产品种类", len(products))
    with col3:
        st.metric("总规格(KG)", f"{products['规格_KG'].sum():,.2f}")
    with col4:
        st.metric("总重量(KG)", f"{products['数量_KG'].sum():,.2f}")
    
    # 数据可视化
    st.subheader("📈 数据可视化分析")
    
    # 产品规格分布
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**产品规格分布**")
        if not products.empty:
            fig = px.histogram(
                products, 
                x='规格_KG', 
                nbins=20,
                title="产品规格分布",
                labels={'规格_KG': '规格 (KG/桶)', 'count': '产品数量'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**单价分布**")
        if not products.empty:
            fig = px.histogram(
                products, 
                x='单价', 
                nbins=20,
                title="产品单价分布",
                labels={'单价': '单价 (元)', 'count': '产品数量'}
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
                default=['产品型号', '产品名称', '规格_KG', '单价', '金额']
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
        quantity_range = st.slider(
            "数量范围",
            float(products['数量_件'].min()),
            float(products['数量_件'].max()),
            (float(products['数量_件'].min()), float(products['数量_件'].max()))
        )
    
    # 应用高级筛选
    advanced_filtered = products[
        (products['金额'] >= price_range[0]) & 
        (products['金额'] <= price_range[1]) &
        (products['规格_KG'] >= spec_range[0]) & 
        (products['规格_KG'] <= spec_range[1]) &
        (products['数量_件'] >= quantity_range[0]) & 
        (products['数量_件'] <= quantity_range[1])
    ]
    
    st.subheader(f"🎯 筛选结果 (共{len(advanced_filtered)}条)")
    
    if not advanced_filtered.empty:
        st.dataframe(
            advanced_filtered[['产品型号', '产品名称', '规格_KG', '数量_件', '单价', '金额']],
            use_container_width=True,
            height=300
        )
        
        # 导出功能
        if st.button("📥 导出筛选结果"):
            csv = advanced_filtered.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 下载CSV",
                data=csv,
                file_name=f'产品筛选结果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mime='text/csv'
            )

# 页脚
st.markdown("---")
st.markdown(
    "🏢 **客户产品管理系统** | "
    "📅 基于Excel数据 | "
    "🕒 创建时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)