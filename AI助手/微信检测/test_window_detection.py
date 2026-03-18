#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试微信窗口检测功能
"""

import ctypes
from ctypes import wintypes


def test_window_detection():
    """测试窗口检测"""
    print("=" * 60)
    print("  测试微信窗口检测")
    print("=" * 60)
    print()
    
    user32 = ctypes.windll.user32
    
    print("正在枚举所有可见窗口...")
    print()
    
    def enum_callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                window_title = title.value
                
                # 打印所有窗口
                print(f"窗口: {window_title}")
                
                # 检查是否是微信窗口
                if '微信' in window_title or 'WeChat' in window_title:
                    print(f"🔍 找到可能的微信窗口: {window_title}")
                    
                    # 获取窗口坐标
                    rect = wintypes.RECT()
                    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                        print(f"   坐标: ({rect.left}, {rect.top}) - ({rect.right}, {rect.bottom})")
                        print(f"   大小: {rect.right - rect.left} x {rect.bottom - rect.top}")
                        print()
        return True
    
    # 枚举所有窗口
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    enum_windows = WNDENUMPROC(enum_callback)
    user32.EnumWindows(enum_windows, 0)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_window_detection()
