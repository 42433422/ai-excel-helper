#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：列出所有可见窗口
帮助诊断微信窗口检测问题
"""

import ctypes
from ctypes import wintypes

def list_visible_windows():
    """列出所有可见窗口"""
    user32 = ctypes.windll.user32
    
    windows = []
    
    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            # 获取窗口标题
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                window_title = title.value
                
                # 获取窗口坐标
                rect = wintypes.RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    
                    # 只显示有实际大小的窗口
                    if width > 100 and height > 100:
                        windows.append({
                            'handle': hwnd,
                            'title': window_title,
                            'left': rect.left,
                            'top': rect.top,
                            'width': width,
                            'height': height
                        })
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM
    )
    
    enum_windows = WNDENUMPROC(enum_callback)
    user32.EnumWindows(enum_windows, 0)
    
    return windows

if __name__ == "__main__":
    print("=" * 80)
    print("所有可见窗口列表")
    print("=" * 80)
    
    windows = list_visible_windows()
    
    # 按标题排序
    windows.sort(key=lambda x: x['title'])
    
    # 打印所有窗口
    for i, win in enumerate(windows, 1):
        print(f"\n{i}. 标题: {win['title']}")
        print(f"   位置: ({win['left']}, {win['top']})")
        print(f"   大小: {win['width']} x {win['height']}")
        print(f"   句柄: {win['handle']}")
    
    print("\n" + "=" * 80)
    print(f"共找到 {len(windows)} 个可见窗口")
    print("=" * 80)
    
    # 查找可能与微信相关的窗口
    print("\n可能与微信相关的窗口：")
    wechat_keywords = ['微信', 'WeChat', 'Weixin', 'Wechat', 'WECHAT']
    wechat_windows = [w for w in windows if any(kw.lower() in w['title'].lower() for kw in wechat_keywords)]
    
    if wechat_windows:
        for win in wechat_windows:
            print(f"  ✓ 找到: {win['title']}")
    else:
        print("  ✗ 未找到包含微信关键词的窗口")
        print("\n建议：")
        print("  1. 确保微信窗口已完全打开（未最小化）")
        print("  2. 确保微信窗口在前台显示")
        print("  3. 检查窗口标题是否包含 '微信' 或 'WeChat'")
