#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标签字体大小分析工具
"""

def analyze_label_fonts():
    """分析标签生成器中的字体大小配置"""
    
    print("=" * 80)
    print("📝 标签字体大小完整配置")
    print("=" * 80)
    
    print("\n🎯 基础字体大小配置（font_sizes字典）:")
    print("┌─────────────────┬──────┬──────────────┐")
    print("│ 字体类型        │ 大小 │ 用途说明     │")
    print("├─────────────────┼──────┼──────────────┤")
    print("│ title           │  36  │ 标题文字     │")
    print("│ value_large     │  60  │ 大值文字     │")
    print("│ value_medium    │  46  │ 中值文字     │")
    print("│ value_small     │  36  │ 小值文字     │")
    print("│ ratio_header    │  32  │ 配比表头     │")
    print("│ ratio_value     │  34  │ 配比数值     │")
    print("│ footer          │  52  │ 底部提示     │")
    print("└─────────────────┴──────┴──────────────┘")
    
    print("\n📋 实际使用的字体大小对照表:")
    print("┌─────────────────┬──────┬──────────────────────────┬─────────────┐")
    print("│ 标签区域        │ 大小 │ 实际调用代码             │ 说明        │")
    print("├─────────────────┼──────┼──────────────────────────┼─────────────┤")
    print("│ 产品编号标签    │  40  │ get_font(40)            │ 字段标签    │")
    print("│ 产品编号数值    │  60  │ get_font(60)            │ 实际数值    │")
    print("│ 产品名称标签    │  40  │ get_font(40)            │ 字段标签    │")
    print("│ 产品名称数值    │  48  │ get_font(48)            │ 实际数值    │")
    print("│ 参考配比标题    │  32  │ get_font(32)            │ 表头        │")
    print("│ 配比表头       │  28  │ get_font(28)            │ 列标题      │")
    print("│ 配比数值       │  30  │ get_font(30)            │ 配比数据    │")
    print("│ 生产日期       │  38  │ get_font(38)            │ 日期信息    │")
    print("│ 底部提示文字   │  48  │ get_font(48)            │ 使用提示    │")
    print("└─────────────────┴──────┴──────────────────────────┴─────────────┘")
    
    print("\n🎨 字体优先级配置:")
    print("1. msyhbd.ttf  - 微软雅黑粗体（优先）")
    print("2. simhei.ttf  - 黑体")
    print("3. simsun.ttc  - 宋体")
    print("4. arial.ttf   - 英文字体")
    print("5. times.ttf   - 英文字体")
    print("6. 系统默认字体（备选）")
    
    print("\n💡 字体大小规律:")
    print("• 字段标签: 40px（清晰标识字段名）")
    print("• 实际数值: 60px/48px（突出重要信息）")
    print("• 日期信息: 38px（中等重要）")
    print("• 配比数据: 28px-34px（表格内容）")
    print("• 提示文字: 48px（醒目提示）")
    
    print("\n🔧 字体大小调整建议:")
    print("• 如果文字太小: 增加字体大小5-10px")
    print("• 如果布局拥挤: 减小字体大小5px")
    print("• 如果需要强调: 使用value_large配置")
    print("• 如果需要紧凑: 使用value_small配置")
    
    print("\n📐 标签尺寸规格:")
    print("• 总尺寸: 900×600像素")
    print("• 边框: 黑色3像素")
    print("• 背景: 白色")
    print("• 分割线: 黑色2像素")

if __name__ == "__main__":
    analyze_label_fonts()
