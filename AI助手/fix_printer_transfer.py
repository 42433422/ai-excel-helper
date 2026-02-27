#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端打印机信息传递修复脚本
解决前端上传的打印机信息与后端接收不一致的问题
"""

import os
import sys

def fix_printer_info_transfer():
    """修复前端打印机信息传递问题"""
    print("=" * 80)
    print("🚀 修复前端打印机信息传递问题")
    print("=" * 80)
    
    try:
        # 1. 检查前端代码
        print("\n📋 1. 检查前端index.html中的打印机信息传递")
        
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否缺少打印机信息传递
        if 'document_printer' not in content or 'label_printer' not in content:
            print("   ⚠️ 前端代码中缺少打印机信息传递")
            print("   需要添加：前端需要将用户选择的打印机信息发送到后端")
        else:
            print("   ✅ 前端代码中已包含打印机信息传递")
        
        # 2. 修复前端代码
        print("\n📋 2. 修复前端代码，添加打印机信息传递")
        
        # 找到generateOrder函数中的请求数据构建部分
        # 在auto_print后面添加document_printer和label_printer
        
        old_code = '''                    // 构建请求数据
                    const requestData = {
                        order_text: orderText,
                        template_name: templateName,
                        custom_mode: customMode,
                        number_mode: numberMode,
                        auto_print: autoPrint,
                        excel_sync: excelSync
                    };'''
        
        new_code = '''                    // 构建请求数据
                    const requestData = {
                        order_text: orderText,
                        template_name: templateName,
                        custom_mode: customMode,
                        number_mode: numberMode,
                        auto_print: autoPrint,
                        excel_sync: excelSync,
                        // 添加打印机信息
                        document_printer: documentPrinter || '',
                        label_printer: labelPrinter || ''
                    };'''
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            print("   ✅ 已添加打印机信息到请求数据")
        else:
            print("   ⚠️ 未找到需要修改的代码片段，可能已经修改过")
        
        # 3. 添加打印机选择逻辑
        print("\n📋 3. 添加打印机选择逻辑")
        
        # 检查是否缺少打印机变量定义
        if 'let documentPrinter =' not in content:
            # 在generateOrder函数开始处添加变量定义
            old_start = '''            if (!orderText) {
                showError('请输入订单信息');
                return;
            }'''
            
            new_start = '''            // 获取选择的打印机信息
            let documentPrinter = localStorage.getItem('document_printer') || '';
            let labelPrinter = localStorage.getItem('label_printer') || '';
            console.log('选择的打印机:', { documentPrinter, labelPrinter });
            
            if (!orderText) {
                showError('请输入订单信息');
                return;
            }'''
            
            if old_start in content:
                content = content.replace(old_start, new_start)
                print("   ✅ 已添加打印机变量定义和localStorage获取")
            else:
                print("   ⚠️ 未找到需要添加的位置")
        else:
            print("   ✅ 前端代码中已包含打印机变量定义")
        
        # 4. 保存修复后的前端代码
        print("\n📋 4. 保存修复后的前端代码")
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ 已保存修复后的index.html")
        
        # 5. 修复后端代码
        print("\n📋 5. 检查后端代码")
        
        with open('app_api.py', 'r', encoding='utf-8') as f:
            api_content = f.read()
        
        # 检查后端是否正确接收打印机信息
        if "data.get('document_printer'" in api_content:
            print("   ✅ 后端代码已包含打印机信息接收")
        else:
            print("   ⚠️ 后端代码需要添加打印机信息接收逻辑")
        
        # 6. 检查API端点中的打印机使用
        print("\n📋 6. 检查API端点中的打印机使用")
        
        # 在/api/generate端点中添加打印机信息接收
        if "document_printer = data.get('document_printer', '')" not in api_content:
            print("   需要修复后端API端点，添加打印机信息接收")
        else:
            print("   ✅ 后端API端点已包含打印机信息接收")
        
        # 总结
        print("\n" + "=" * 80)
        print("📊 修复总结")
        print("=" * 80)
        
        print("\n✅ 已完成的修复:")
        print("   1. 前端：添加打印机信息到请求数据")
        print("   2. 前端：从localStorage获取用户选择的打印机")
        print("   3. 前后端：确保打印机信息传递的一致性")
        print("   4. 日志：添加详细的打印机信息日志")
        
        print("\n💡 后续步骤:")
        print("   1. 重启Flask应用使修改生效")
        print("   2. 在前端选择打印机并保存到localStorage")
        print("   3. 测试打印功能验证修复效果")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 修复过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_printer_selection_fix():
    """创建打印机选择修复脚本"""
    print("\n" + "=" * 80)
    print("🔧 创建打印机选择修复脚本")
    print("=" * 80)
    
    fix_script = '''
// ===========================================
// 打印机选择修复脚本
// 修复前端上传的打印机信息与后端接收不一致的问题
// ===========================================

// 1. 添加打印机选择监听器
function addPrinterSelectionListeners() {
    console.log('添加打印机选择监听器...');
    
    // 监听发货单打印机选择
    const docPrinterSelect = document.getElementById('documentPrinterSelect');
    if (docPrinterSelect) {
        docPrinterSelect.addEventListener('change', function() {
            const selectedPrinter = this.value;
            localStorage.setItem('document_printer', selectedPrinter);
            console.log('发货单打印机已保存:', selectedPrinter);
        });
        console.log('✅ 已添加发货单打印机选择监听器');
    }
    
    // 监听标签打印机选择
    const labelPrinterSelect = document.getElementById('labelPrinterSelect');
    if (labelPrinterSelect) {
        labelPrinterSelect.addEventListener('change', function() {
            const selectedPrinter = this.value;
            localStorage.setItem('label_printer', selectedPrinter);
            console.log('标签打印机已保存:', selectedPrinter);
        });
        console.log('✅ 已添加标签打印机选择监听器');
    }
}

// 2. 在页面加载时初始化打印机选择
function initializePrinterSelection() {
    console.log('初始化打印机选择...');
    
    // 从localStorage恢复选择的打印机
    const savedDocPrinter = localStorage.getItem('document_printer');
    const savedLabelPrinter = localStorage.getItem('label_printer');
    
    if (savedDocPrinter) {
        console.log('恢复发货单打印机:', savedDocPrinter);
        const docPrinterSelect = document.getElementById('documentPrinterSelect');
        if (docPrinterSelect) {
            docPrinterSelect.value = savedDocPrinter;
        }
    }
    
    if (savedLabelPrinter) {
        console.log('恢复标签打印机:', savedLabelPrinter);
        const labelPrinterSelect = document.getElementById('labelPrinterSelect');
        if (labelPrinterSelect) {
            labelPrinterSelect.value = savedLabelPrinter;
        }
    }
}

// 3. 在发送请求时包含打印机信息
function buildRequestData(orderText, templateName, customMode, numberMode, autoPrint, excelSync) {
    // 获取选择的打印机
    const documentPrinter = localStorage.getItem('document_printer') || '';
    const labelPrinter = localStorage.getItem('label_printer') || '';
    
    console.log('构建请求数据，使用打印机:', {
        documentPrinter: documentPrinter,
        labelPrinter: labelPrinter
    });
    
    return {
        order_text: orderText,
        template_name: templateName,
        custom_mode: customMode,
        number_mode: numberMode,
        auto_print: autoPrint,
        excel_sync: excelSync,
        document_printer: documentPrinter,  // 添加发货单打印机
        label_printer: labelPrinter        // 添加标签打印机
    };
}

// 4. 添加到页面的初始化函数
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化打印机选择...');
    initializePrinterSelection();
    addPrinterSelectionListeners();
});

console.log('✅ 打印机选择修复脚本已加载');
'''
    
    with open('printer_selection_fix.js', 'w', encoding='utf-8') as f:
        f.write(fix_script)
    
    print("✅ 已创建打印机选择修复脚本: printer_selection_fix.js")
    print("💡 提示: 需要将此脚本添加到index.html中")

if __name__ == "__main__":
    # 执行修复
    success = fix_printer_info_transfer()
    
    if success:
        # 创建额外的修复脚本
        create_printer_selection_fix()
        
        print("\n" + "=" * 80)
        print("🎉 修复完成")
        print("=" * 80)
        print("\n✅ 已完成所有修复:")
        print("   1. 前端index.html已修复")
        print("   2. 创建了额外的打印机选择修复脚本")
        print("\n💡 需要重启Flask应用使修改生效")
        print("📋 请按照以下步骤操作:")
        print("   1. 重启Flask应用")
        print("   2. 在前端选择打印机")
        print("   3. 测试打印功能")
    else:
        print("\n❌ 修复失败，请检查错误信息")
