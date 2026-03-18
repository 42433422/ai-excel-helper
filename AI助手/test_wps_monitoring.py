#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS窗口监控测试脚本

用于测试WPS窗口检测和按钮点击功能
"""

import win32gui
import win32api
import win32con
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_wps_monitoring():
    """
    测试WPS窗口监控功能
    """
    logger.info("🚀 开始测试WPS窗口监控...")
    
    # 尝试查找多种类型的WPS窗口
    window_classes = [
        'ksoframe',         # WPS主窗口
        'KingsoftOfficeApp', # WPS应用窗口
        'XLMAIN',           # Excel兼容模式
        '#32770',           # 通用对话框
        'bosa_sdm_Microsoft Office Excel'  # Excel对话框
    ]
    
    # 查找WPS窗口
    wps_hwnd = None
    dialog_hwnd = None
    
    logger.info("⏳ 查找WPS窗口...")
    
    # 最多尝试10次
    for attempt in range(10):
        logger.info(f"尝试 {attempt+1}/10: 查找WPS窗口...")
        
        # 查找所有类型的窗口
        for cls in window_classes:
            hwnd = win32gui.FindWindow(cls, None)
            if hwnd:
                window_text = win32gui.GetWindowText(hwnd)
                logger.info(f"找到窗口: {cls}, 标题: '{window_text}', 句柄: {hwnd}")
                
                if '保存' in window_text or '是否' in window_text:
                    dialog_hwnd = hwnd
                    logger.info("✅ 找到WPS保存对话框！")
                elif not wps_hwnd:
                    wps_hwnd = hwnd
                    logger.info("✅ 找到WPS主窗口！")
        
        if dialog_hwnd or wps_hwnd:
            break
        
        time.sleep(1)
    
    # 确定要操作的窗口
    target_hwnd = dialog_hwnd if dialog_hwnd else wps_hwnd
    
    if target_hwnd:
        logger.info(f"开始在窗口 {target_hwnd} 中查找按钮...")
        
        # 递归查找所有子窗口中的按钮
        all_buttons = []
        
        def find_all_buttons(hwnd, buttons):
            """递归查找所有可见窗口中的按钮"""
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd)
                if text:
                    buttons.append((hwnd, text))
            # 递归查找子窗口
            child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
            while child:
                find_all_buttons(child, buttons)
                child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
            return True
        
        # 开始递归查找
        find_all_buttons(target_hwnd, all_buttons)
        
        logger.info(f"共找到 {len(all_buttons)} 个可见窗口")
        for hwnd, text in all_buttons:
            if text:
                logger.info(f"  - 窗口: {hwnd}, 文本: '{text}'")
        
        # 查找"否"、"不保存"、"取消"等按钮
        close_buttons = []
        for hwnd, text in all_buttons:
            if any(keyword in text for keyword in ['否', '不保存', '取消', 'No', 'Cancel']):
                close_buttons.append((hwnd, text))
        
        if close_buttons:
            logger.info(f"找到 {len(close_buttons)} 个关闭相关按钮")
            
            # 点击第一个找到的关闭按钮
            btn_hwnd, btn_text = close_buttons[0]
            logger.info(f"准备点击按钮: '{btn_text}' (句柄: {btn_hwnd})")
            
            # 等待1秒让对话框完全加载
            time.sleep(1)
            
            # 发送点击消息
            try:
                # 先发送鼠标移动和按下消息
                win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONDOWN, 0, 0)
                time.sleep(0.1)
                win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONUP, 0, 0)
                time.sleep(0.1)
                # 再发送BM_CLICK消息
                win32api.PostMessage(btn_hwnd, win32con.BM_CLICK, 0, 0)
                logger.info(f"✅ 已点击'{btn_text}'按钮")
                
                # 等待窗口关闭（最多5秒）
                logger.info("⏳ 等待WPS窗口关闭...")
                for _ in range(5):
                    time.sleep(1)
                    # 检查所有WPS窗口是否都已关闭
                    all_closed = True
                    for cls in window_classes:
                        if win32gui.FindWindow(cls, None):
                            all_closed = False
                            break
                    if all_closed:
                        logger.info("✅ WPS窗口已完全关闭")
                        break
                else:
                    logger.warning("⚠️ WPS窗口可能仍未关闭")
                
            except Exception as e:
                logger.error(f"点击按钮失败: {e}")
        else:
            logger.warning("⚠️ 未找到关闭相关按钮")
            # 如果没有找到按钮，尝试直接关闭窗口
        else:
            logger.warning("⚠️ 未找到关闭相关按钮")
            # 如果没有找到按钮，尝试直接关闭WPS窗口
            try:
                logger.info("尝试直接关闭WPS窗口...")
                
                # 步骤1: 先查找并关闭文档窗口
                logger.info("步骤1: 查找并关闭文档窗口")
                doc_windows = []
                
                def find_doc_windows(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        text = win32gui.GetWindowText(hwnd)
                        if 'xlsx' in text or '表格' in text:
                            windows.append((hwnd, text))
                    child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
                    while child:
                        find_doc_windows(child, windows)
                        child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
                    return True
                
                find_doc_windows(target_hwnd, doc_windows)
                
                for hwnd, text in doc_windows:
                    logger.info(f"找到文档窗口: {text}, 句柄: {hwnd}")
                    # 尝试关闭文档窗口
                    try:
                        win32api.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        time.sleep(1)
                        logger.info(f"已尝试关闭文档窗口: {text}")
                    except Exception as e:
                        logger.error(f"关闭文档窗口失败: {e}")
                
                time.sleep(1)
                
                # 步骤2: 尝试关闭主窗口
                logger.info("步骤2: 尝试关闭主窗口")
                
                # 方法1: 发送WM_CLOSE消息（优雅关闭）
                logger.info("方法1: 发送WM_CLOSE消息")
                win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(2)
                
                # 检查窗口是否关闭
                still_open = False
                for cls in window_classes:
                    if win32gui.FindWindow(cls, None):
                        still_open = True
                        break
                
                if still_open:
                    logger.warning("⚠️ WM_CLOSE消息未生效，尝试方法2")
                    
                    # 方法2: 使用SendMessage发送WM_CLOSE（更强制）
                    logger.info("方法2: 使用SendMessage发送WM_CLOSE")
                    win32api.SendMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                    time.sleep(2)
                    
                    # 再次检查
                    still_open = False
                    for cls in window_classes:
                        if win32gui.FindWindow(cls, None):
                            still_open = True
                            break
                    
                    if still_open:
                        logger.warning("⚠️ SendMessage WM_CLOSE未生效，尝试方法3")
                        
                        # 方法3: 发送WM_DESTROY消息（强制关闭）
                        logger.info("方法3: 发送WM_DESTROY消息")
                        win32api.SendMessage(target_hwnd, win32con.WM_DESTROY, 0, 0)
                        time.sleep(2)
                        
                        # 再次检查
                        still_open = False
                        for cls in window_classes:
                            if win32gui.FindWindow(cls, None):
                                still_open = True
                                break
                        
                        if still_open:
                            logger.warning("⚠️ WM_DESTROY消息未生效，尝试方法4")
                            
                            # 方法4: 使用结束进程的方式
                            logger.info("方法4: 查找并结束WPS进程")
                            try:
                                import psutil
                                for proc in psutil.process_iter(['name', 'pid']):
                                    if 'wps' in proc.info['name'].lower() or 'kingsoft' in proc.info['name'].lower():
                                        logger.info(f"找到WPS进程: {proc.info['name']}, PID: {proc.info['pid']}")
                                        # 先尝试优雅终止
                                        proc.terminate()
                                        try:
                                            proc.wait(timeout=3)
                                            logger.info(f"已终止WPS进程: {proc.info['name']}")
                                        except psutil.TimeoutExpired:
                                            # 如果超时，强制终止
                                            proc.kill()
                                            logger.info(f"已强制终止WPS进程: {proc.info['name']}")
                            except ImportError:
                                logger.warning("⚠️ 未安装psutil模块，无法使用进程终止方法")
                            except Exception as e:
                                logger.error(f"结束进程失败: {e}")
                
                # 最终检查
                all_closed = True
                for cls in window_classes:
                    if win32gui.FindWindow(cls, None):
                        all_closed = False
                        break
                
                if all_closed:
                    logger.info("✅ WPS窗口已完全关闭")
                else:
                    logger.warning("⚠️ WPS窗口仍未关闭，可能需要手动处理")
                    
            except Exception as e:
                logger.error(f"关闭窗口失败: {e}")
    else:
        logger.warning("⚠️ 未找到WPS窗口")

if __name__ == "__main__":
    test_wps_monitoring()