# 产品信息管理系统

## 项目概述

本项目用于从Excel发货单中提取产品信息，并进行管理和分析。系统包括数据提取、数据库管理和前端可视化功能。

## 文件结构

- **customer_products_final_corrected.db** - 最终修正后的SQLite数据库，包含所有客户和产品信息
- **发货单/** - 原始Excel发货单文件（17个文件）
- **Python脚本** - 用于数据提取、处理和可视化的各种脚本

## 主要功能

1. **数据提取**：从Excel文件中精确提取客户和产品信息
2. **数据库管理**：将提取的数据存储到SQLite数据库中
3. **前端可视化**：通过Streamlit应用展示数据
4. **数据分析**：提供各种统计和分析功能

## 快速开始

### 1. 运行前端应用

```bash
python -m streamlit run web_interface_final.py
```

然后在浏览器中访问：http://localhost:8501

### 2. 重新提取数据

如果需要重新提取数据，可以运行以下命令：

```bash
python exact_column_extraction.py
```

### 3. 验证数据

```bash
python verify_exact_extraction.py
python verify_customer_info.py
```

## 核心脚本说明

- **exact_column_extraction.py** - 精确提取产品信息的主要脚本
- **web_interface_final.py** - Streamlit前端应用
- **verify_exact_extraction.py** - 验证产品信息提取
- **verify_customer_info.py** - 验证客户信息提取

## 技术栈

- Python 3.11+
- pandas - 数据处理
- openpyxl - Excel文件处理
- sqlite3 - 数据库管理
- streamlit - 前端应用
- plotly - 数据可视化

## 数据说明

- 客户数量：17个
- 产品数量：约2000种
- 总金额：根据实际数据统计
- 总重量：根据实际数据统计

## 更新日志

- 2026-01-25：修复购买单位信息提取问题，添加数据刷新功能
- 2026-01-24：实现精确列提取，修复产品信息提取错误
- 2026-01-23：初始版本开发

## 注意事项

1. 确保已安装所有依赖包
2. 运行脚本前确保发货单目录存在
3. 数据库文件会在运行提取脚本时自动更新
4. 前端应用会自动加载最新的数据库数据

## 联系方式

如有问题，请联系相关技术人员。