#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级打印机问题诊断工具
深入分析打印机配置和潜在问题
"""

import sys
import os
import win32print
import win32con

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def advanced_printer_diagnosis():
    """高级打印机诊断"""
    print("=" * 80)
    print("🔍 高级打印机问题诊断工具")
    print("=" * 80)
    
    try:
        # 1. 检查Windows默认打印机
        print("\n📋 1. Windows默认打印机检查")
        try:
            default_printer = win32print.GetDefaultPrinter()
            print(f"   ✅ Windows默认打印机: {default_printer}")
            
            # 检查默认打印机是否为我们的配置之一
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            printer_names = [p[2] for p in printers]
            
            if default_printer in printer_names:
                print(f"   ✅ 默认打印机在可用列表中")
            else:
                print(f"   ⚠️ 默认打印机不在可用列表中")
                
        except Exception as e:
            print(f"   ❌ 无法获取默认打印机: {e}")
        
        # 2. 详细打印机状态检查
        print("\n🔍 2. 详细打印机状态检查")
        try:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            
            for i, printer in enumerate(printers, 1):
                printer_name = printer[2]
                print(f"\n   📄 打印机 {i}: {printer_name}")
                
                try:
                    # 获取打印机句柄
                    hPrinter = win32print.OpenPrinter(printer_name)
                    
                    # 获取打印机信息
                    printer_info = win32print.GetPrinter(hPrinter, 2)
                    
                    # 解析状态
                    status = printer_info.get('Status', '未知')
                    print(f"      📊 状态码: {status}")
                    
                    # 解析属性
                    attributes = printer_info.get('Attributes', 0)
                    is_default = bool(attributes & win32con.PRINTER_ATTRIBUTE_DEFAULT)
                    is_network = bool(attributes & win32con.PRINTER_ATTRIBUTE_NETWORK)
                    is_shared = bool(attributes & win32con.PRINTER_ATTRIBUTE_SHARED)
                    
                    print(f"      🏷️ 默认打印机: {'是' if is_default else '否'}")
                    print(f"      🌐 网络打印机: {'是' if is_network else '否'}")
                    print(f"      🤝 共享打印机: {'是' if is_shared else '否'}")
                    
                    # 检查是否有正在等待的打印作业
                    jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                    if jobs:
                        print(f"      📝 等待的打印作业: {len(jobs)} 个")
                        for job in jobs:
                            print(f"         - 作业ID: {job['JobId']}, 状态: {job['Status']}, 文档: {job['pDocument']}")
                    else:
                        print(f"      ✅ 没有等待的打印作业")
                    
                    win32print.ClosePrinter(hPrinter)
                    
                except Exception as e:
                    print(f"      ❌ 无法获取详细信息: {e}")
            
        except Exception as e:
            print(f"   ❌ 打印机状态检查失败: {e}")
        
        # 3. 测试打印到文件功能
        print("\n🧪 3. 测试打印功能")
        try:
            # 创建测试文件
            test_content = "打印机功能测试\n日期: 2026-02-02\n"
            test_file = "test_print.txt"
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            print(f"   📄 创建测试文件: {test_file}")
            
            # 测试每个打印机
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            for i, printer in enumerate(printers[:3], 1):  # 只测试前3个
                printer_name = printer[2]
                print(f"\n   🧪 测试打印机 {i}: {printer_name}")
                
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    
                    # 创建打印作业
                    dc = win32print.CreateDC("WINSPOOL", printer_name)
                    win32print.StartDoc(dc, ("Test Print Job", None))
                    win32print.StartPage(dc)
                    
                    # 写入测试内容
                    win32print.TextOut(dc, 100, 100, "打印机测试", 8)
                    
                    win32print.EndPage(dc)
                    win32print.EndDoc(dc)
                    win32print.DeleteDC(dc)
                    win32print.ClosePrinter(hPrinter)
                    
                    print(f"      ✅ 测试成功")
                    
                except Exception as e:
                    print(f"      ❌ 测试失败: {e}")
            
            # 清理测试文件
            if os.path.exists(test_file):
                os.remove(test_file)
                
        except Exception as e:
            print(f"   ❌ 打印功能测试失败: {e}")
        
        # 4. 检查打印机队列
        print("\n📋 4. 检查打印机队列")
        try:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
            
            for i, printer in enumerate(printers[:2], 1):  # 检查前2个
                printer_name = printer[2]
                print(f"\n   📋 打印机 {i}: {printer_name}")
                
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    
                    # 获取打印队列信息
                    jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                    
                    if jobs:
                        print(f"      📝 当前有 {len(jobs)} 个作业:")
                        for job in jobs:
                            job_info = {
                                'id': job['JobId'],
                                'status': job['Status'],
                                'priority': job['Priority'],
                                'size': job['Size'],
                                'submitted': job['Submitted'],
                                'document': job['pDocument']
                            }
                            print(f"         - 作业ID: {job_info['id']}")
                            print(f"           文档: {job_info['document']}")
                            print(f"           状态: {job_info['status']}")
                            print(f"           优先级: {job_info['priority']}")
                    else:
                        print(f"      ✅ 队列为空")
                    
                    win32print.ClosePrinter(hPrinter)
                    
                except Exception as e:
                    print(f"      ❌ 无法检查队列: {e}")
                    
        except Exception as e:
            print(f"   ❌ 队列检查失败: {e}")
        
        # 5. 权限和配置检查
        print("\n🔐 5. 权限和配置检查")
        try:
            # 检查当前用户权限
            import ctypes
            current_user = ctypes.windll.advapi32.GetUserSidString()
            print(f"   👤 当前用户SID: {current_user}")
            
            # 检查是否有打印机配置权限
            for i, printer in enumerate(printers[:2], 1):
                printer_name = printer[2]
                print(f"\n   🔐 打印机 {i}: {printer_name}")
                
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)
                    printer_info = win32print.GetPrinter(hPrinter, 2)
                    security_info = printer_info.get('pSecurityDescriptor', None)
                    
                    if security_info:
                        print(f"      ✅ 有安全描述符")
                    else:
                        print(f"      ⚠️ 无安全描述符")
                    
                    win32print.ClosePrinter(hPrinter)
                    
                except Exception as e:
                    print(f"      ❌ 权限检查失败: {e}")
                    
        except Exception as e:
            print(f"   ❌ 权限检查失败: {e}")
        
        print("\n" + "=" * 80)
        print("✅ 高级诊断完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    advanced_printer_diagnosis()
