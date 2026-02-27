#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信窗口识别模块
自动检测微信窗口位置、大小，并定位关键区域
"""

import sys
import os
import time
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WeChatWindowInfo:
    """微信窗口信息"""
    handle: int           # 窗口句柄
    title: str            # 窗口标题
    left: int             # 左边界
    top: int              # 上边界
    width: int            # 宽度
    height: int           # 高度
    is_maximized: bool    # 是否最大化
    is_minimized: bool    # 是否最小化

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def center(self) -> Tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        """返回 (left, top, right, bottom)"""
        return (self.left, self.top, self.right, self.bottom)

    def to_dict(self) -> Dict:
        return {
            "handle": self.handle,
            "title": self.title,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "is_maximized": self.is_maximized,
            "is_minimized": self.is_minimized
        }


class WeChatWindowDetector:
    """微信窗口检测器"""

    WECHAT_WINDOW_TITLES = [
        "微信",
        "WeChat",
        "微信PC版",
        "文件传输助手",
        "聊天",
    ]

    def __init__(self):
        self.last_window_info: Optional[WeChatWindowInfo] = None
        self.pywinauto_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖是否可用"""
        try:
            import pywinauto
            self.pywinauto_available = True
            logger.info("pywinauto 初始化成功")
        except ImportError:
            logger.warning("pywinauto 未安装，将使用备用方案")

    def find_wechat_window(self) -> Optional[WeChatWindowInfo]:
        """
        查找微信窗口

        Returns:
            WeChatWindowInfo 或 None
        """
        # 优先使用ctypes备用方案，它更可靠
        result = self._find_with_ctypes()
        if result:
            return result
        # 如果ctypes失败，再尝试pywinauto
        if self.pywinauto_available:
            return self._find_with_pywinauto()
        return None

    def _find_with_pywinauto(self) -> Optional[WeChatWindowInfo]:
        """使用 pywinauto 查找窗口"""
        try:
            import pywinauto
            from pywinauto import Application

            # 尝试查找所有正在运行的窗口
            try:
                # 方法1：尝试连接任何包含微信关键词的窗口
                app = Application(backend="uia").connect(title_re=".*微信.*|.*WeChat.*", timeout=3)
                window = app.window(title_re=".*微信.*|.*WeChat.*")
                
                if not window.exists(timeout=3):
                    # 方法2：尝试查找所有可见窗口
                    desktop = Application(backend="uia").connect(handle=0)
                    window = desktop.window(title_re=".*微信.*|.*WeChat.*")
            except:
                # 方法3：尝试通过进程名查找
                try:
                    app = Application(backend="uia").connect(path="WeChat.exe", timeout=3)
                    # 获取所有窗口并查找可见的
                    for win in app.windows():
                        if win.exists() and win.is_visible():
                            window = win
                            break
                    else:
                        return None
                except:
                    # 微信可能未运行
                    logger.error("pywinauto 查找窗口失败: Process 'WeChat.exe' not found!")
                    return None

            # 获取窗口信息
            if window.exists(timeout=3):
                window.set_focus()
                time.sleep(0.2)  # 等待窗口激活

                # 获取窗口的实际坐标
                rect = window.rectangle()
                left = rect.left
                top = rect.top
                width = rect.width()
                height = rect.height()

                info = WeChatWindowInfo(
                    handle=int(window.handle),
                    title=window.window_text(),
                    left=int(left),
                    top=int(top),
                    width=int(width),
                    height=int(height),
                    is_maximized=bool(window.is_maximized()),
                    is_minimized=bool(window.is_minimized())
                )

                self.last_window_info = info
                logger.info(f"找到微信窗口: {info.title} at ({info.left}, {info.top})")
                return info

        except Exception as e:
            logger.error(f"pywinauto 查找窗口失败: {e}")

        return None

    def _find_with_ctypes(self) -> Optional[WeChatWindowInfo]:
        """使用 ctypes 备用查找方案"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # 存储结果的列表
            handles = []

            def enum_callback(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    # 获取窗口标题
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        title = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, title, length + 1)
                        window_title = title.value
                        
                        # 调试：打印所有可见窗口标题
                        # print(f"找到窗口: {window_title}")
                        
                        # 检查是否是微信窗口
                        # 条件1：标题包含微信、WeChat或Weixin
                        contains_wechat = any(keyword in window_title for keyword in ['微信', 'WeChat', 'Weixin'])
                        # 条件2：排除浏览器和Web UI窗口
                        is_browser = any(browser in window_title for browser in ['浏览器', 'Edge', 'Chrome', 'Firefox', 'Safari'])
                        is_web_ui = '微信助手 - Web界面' in window_title
                        # 条件3：排除其他辅助窗口
                        is_valid = contains_wechat and not is_browser and not is_web_ui
                        
                        if is_valid:
                            # 获取窗口坐标
                            rect = wintypes.RECT()
                            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                                info = WeChatWindowInfo(
                                    handle=hwnd,
                                    title=window_title,
                                    left=rect.left,
                                    top=rect.top,
                                    width=rect.right - rect.left,
                                    height=rect.bottom - rect.top,
                                    is_maximized=False,
                                    is_minimized=False
                                )
                                handles.append(info)
                return True

            # 枚举所有窗口
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM
            )

            enum_windows = WNDENUMPROC(enum_callback)
            user32.EnumWindows(enum_windows, 0)

            if handles:
                # 返回第一个匹配的窗口
                self.last_window_info = handles[0]
                logger.info(f"找到微信窗口: {handles[0].title} at ({handles[0].left}, {handles[0].top})")
                return handles[0]

        except Exception as e:
            logger.error(f"ctypes 查找窗口失败: {e}")

        return None

    def get_chat_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """
        获取聊天区域坐标

        微信窗口布局为：
        - 左侧：联系人目录（约100px）
        - 中间：聊天列表（约250px）
        - 右侧：聊天内容主区域（剩余空间）

        Returns:
            (left, top, right, bottom) - 只返回聊天内容主区域
        """
        # 微信标准布局
        contact_list_width = 100    # 左侧联系人目录
        chat_list_width = 250       # 中间聊天列表
        total_sidebar = contact_list_width + chat_list_width  # 总侧边栏宽度

        # 顶部标题栏高度 - 根据窗口高度动态计算
        header_height = max(60, min(100, int(window_info.height * 0.08)))

        # 底部输入区域高度 - 根据窗口高度动态计算
        input_height = max(120, min(200, int(window_info.height * 0.15)))

        # 聊天内容区域：从总侧边栏右侧开始，到窗口右侧
        chat_left = window_info.left + total_sidebar
        chat_top = window_info.top + header_height
        chat_right = window_info.right - 20  # 右边距
        chat_bottom = window_info.bottom - input_height

        # 确保坐标有效
        if chat_left >= chat_right or chat_top >= chat_bottom:
            # 如果计算失败，使用备用方案
            chat_left = window_info.left + 350
            chat_top = window_info.top + 80
            chat_right = window_info.right - 20
            chat_bottom = window_info.bottom - 150

        return (chat_left, chat_top, chat_right, chat_bottom)

    def get_sidebar_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """获取侧边栏区域（左上部分）"""
        contact_list_width = 100
        chat_list_width = 250
        
        return (
            window_info.left,
            window_info.top + 60,
            window_info.left + contact_list_width + chat_list_width,
            window_info.bottom - 150
        )

    def get_title_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """获取标题栏区域（顶部）"""
        header_height = max(60, min(100, int(window_info.height * 0.08)))
        
        return (
            window_info.left + 350,
            window_info.top,
            window_info.right,
            window_info.top + header_height
        )

    def get_input_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """
        获取输入框区域坐标

        Returns:
            (left, top, right, bottom)
        """
        # 输入框通常在窗口底部
        # 宽度约占主聊天区域的80%
        # 高度约80-100px

        sidebar_width = 250
        input_height = 120

        input_left = window_info.left + sidebar_width + 20
        input_right = window_info.right - 100
        input_top = window_info.bottom - input_height - 20
        input_bottom = window_info.bottom - 30

        return (input_left, input_top, input_right, input_bottom)

    def get_send_button_pos(self, window_info: WeChatWindowInfo) -> Tuple[int, int]:
        """
        获取发送按钮位置

        Returns:
            (x, y) 坐标
        """
        sidebar_width = 250
        input_height = 120

        # 发送按钮通常在输入框右侧
        send_x = window_info.right - 70
        send_y = window_info.bottom - 60

        return (send_x, send_y)
    
    def get_search_box_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """
        获取搜索框区域坐标（微信窗口顶部）

        Returns:
            (left, top, right, bottom)
        """
        # 搜索框通常在顶部导航栏，宽度约200-300，高度约30-40
        search_width = 250
        search_height = 35
        search_x = window_info.left + 10
        search_y = window_info.top + 10

        return (search_x, search_y, search_x + search_width, search_y + search_height)
    
    def get_contact_list_area(self, window_info: WeChatWindowInfo) -> Tuple[int, int, int, int]:
        """
        获取联系人/聊天列表区域坐标

        Returns:
            (left, top, right, bottom)
        """
        # 联系人列表在侧边栏，宽度约250
        sidebar_width = 250
        sidebar_x = window_info.left + 10
        sidebar_y = window_info.top + 60
        sidebar_bottom = window_info.bottom - 50

        return (sidebar_x, sidebar_y, sidebar_x + sidebar_width, sidebar_bottom)

    def focus_window(self, window_info: WeChatWindowInfo) -> bool:
        """将微信窗口置顶并激活"""
        try:
            import pywinauto
            app = Application(backend="uia").connect(handle=window_info.handle)
            window = app.window(handle=window_info.handle)
            window.set_focus()
            window.restore()  # 如果最小化则恢复
            time.sleep(0.3)  # 等待窗口激活
            logger.info(f"已激活微信窗口")
            return True
        except Exception as e:
            logger.error(f"激活窗口失败: {e}")
            return False

    def wait_for_wechat(self, timeout: float = 30.0) -> Optional[WeChatWindowInfo]:
        """等待微信窗口出现"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            window = self.find_wechat_window()
            if window:
                return window
            time.sleep(1)

        logger.warning(f"等待 {timeout}秒 后未找到微信窗口")
        return None


class WeChatElementLocator:
    """微信界面元素定位器"""

    def __init__(self, window_info: WeChatWindowInfo):
        self.window_info = window_info

    def locate_chat_list(self) -> Tuple[int, int, int, int]:
        """定位聊天列表区域（左侧）"""
        chat_list_left = self.window_info.left + 10
        chat_list_top = self.window_info.top + 60
        chat_list_right = self.window_info.left + 250
        chat_list_bottom = self.window_info.bottom - 50

        return (chat_list_left, chat_list_top, chat_list_right, chat_list_bottom)

    def locate_message_area(self) -> Tuple[int, int, int, int]:
        """定位消息显示区域（中间主区域）"""
        msg_left = self.window_info.left + 270
        msg_top = self.window_info.top + 60
        msg_right = self.window_info.right - 20
        msg_bottom = self.window_info.bottom - 180

        return (msg_left, msg_top, msg_right, msg_bottom)

    def locate_input_box(self) -> Tuple[int, int, int, int]:
        """定位输入框区域"""
        input_left = self.window_info.left + 280
        input_top = self.window_info.bottom - 150
        input_right = self.window_info.right - 100
        input_bottom = self.window_info.bottom - 50

        return (input_left, input_top, input_right, input_bottom)

    def locate_send_button(self) -> Tuple[int, int]:
        """定位发送按钮中心坐标"""
        send_x = self.window_info.right - 60
        send_y = self.window_info.bottom - 90

        return (send_x, send_y)


def test_wechat_detection():
    """测试窗口检测"""
    print("=" * 60)
    print("  微信窗口检测测试")
    print("=" * 60)
    print()

    detector = WeChatWindowDetector()

    print("正在查找微信窗口...")
    window_info = detector.find_wechat_window()

    if window_info:
        print(f"\n✅ 找到微信窗口！")
        print(f"  窗口标题: {window_info.title}")
        print(f"  窗口位置: ({window_info.left}, {window_info.top})")
        print(f"  窗口大小: {window_info.width} x {window_info.height}")
        print(f"  句柄: {window_info.handle}")

        print(f"\n  聊天区域: {detector.get_chat_area(window_info)}")
        print(f"  输入区域: {detector.get_input_area(window_info)}")
        print(f"  发送按钮: {detector.get_send_button_pos(window_info)}")

        # 测试聚焦窗口
        print(f"\n  正在激活窗口...")
        if detector.focus_window(window_info):
            print("  ✅ 窗口已激活")
    else:
        print("\n❌ 未找到微信窗口")
        print("  请确保微信PC版已打开")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    test_wechat_detection()
