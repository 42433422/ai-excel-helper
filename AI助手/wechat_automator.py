#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信自动化操作模块
自动点击输入框、发送消息等操作
"""

import sys
import os
import time
import logging
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AutomationResult:
    """操作结果"""
    success: bool
    message: str
    details: Dict = None


class WeChatAutomator:
    """微信自动化操作器"""

    def __init__(self):
        self.pyautogui_available = False
        self.keyboard_available = False
        self._check_dependencies()
        self.last_position = (0, 0)

    def _check_dependencies(self):
        """检查依赖"""
        try:
            import pyautogui
            self.pyautogui_available = True
            pyautogui.FAIL_SAFE = True
            pyautogui.PAUSE = 0.1
            logger.info("PyAutoGUI 初始化成功")
        except ImportError:
            logger.warning("PyAutoGUI 未安装")

        try:
            import keyboard
            self.keyboard_available = True
            logger.info("keyboard 初始化成功")
        except ImportError:
            logger.warning("keyboard 未安装")

    def click_input_box(self, window_info) -> AutomationResult:
        """
        点击输入框

        Args:
            window_info: 窗口信息

        Returns:
            AutomationResult: 操作结果
        """
        try:
            from wechat_window import WeChatWindowDetector

            detector = WeChatWindowDetector()
            input_area = detector.get_input_area(window_info)

            # 点击输入框中心
            click_x = (input_area[0] + input_area[2]) // 2
            click_y = (input_area[1] + input_area[3]) // 2

            if self._click(click_x, click_y):
                self.last_position = (click_x, click_y)
                return AutomationResult(
                    success=True,
                    message="已点击输入框",
                    details={"position": (click_x, click_y)}
                )
            else:
                return AutomationResult(
                    success=False,
                    message="点击输入框失败"
                )

        except Exception as e:
            logger.error(f"点击输入框失败: {e}")
            return AutomationResult(
                success=False,
                message=f"点击输入框出错: {str(e)}"
            )

    def click_send_button(self, window_info) -> AutomationResult:
        """
        点击发送按钮

        Args:
            window_info: 窗口信息

        Returns:
            AutomationResult: 操作结果
        """
        try:
            from wechat_window import WeChatWindowDetector

            detector = WeChatWindowDetector()
            send_pos = detector.get_send_button_pos(window_info)

            if self._click(send_pos[0], send_pos[1]):
                return AutomationResult(
                    success=True,
                    message="已点击发送按钮",
                    details={"position": send_pos}
                )
            else:
                return AutomationResult(
                    success=False,
                    message="点击发送按钮失败"
                )

        except Exception as e:
            logger.error(f"点击发送按钮失败: {e}")
            return AutomationResult(
                success=False,
                message=f"点击发送按钮出错: {str(e)}"
            )
    
    def search_contact(self, window_info, contact_name: str) -> AutomationResult:
        """
        在微信中搜索联系人

        Args:
            window_info: 窗口信息
            contact_name: 要搜索的联系人名称

        Returns:
            AutomationResult: 操作结果
        """
        try:
            from wechat_window import WeChatWindowDetector

            detector = WeChatWindowDetector()
            
            # 1. 点击搜索框
            search_area = detector.get_search_box_area(window_info)
            search_x = (search_area[0] + search_area[2]) // 2
            search_y = (search_area[1] + search_area[3]) // 2
            
            if not self._click(search_x, search_y):
                return AutomationResult(
                    success=False,
                    message="无法点击搜索框"
                )
            
            time.sleep(0.3)
            
            # 2. 输入联系人名称
            type_result = self.type_message(contact_name)
            if not type_result.success:
                return AutomationResult(
                    success=False,
                    message="无法输入联系人名称"
                )
            
            time.sleep(0.5)  # 等待搜索结果
            
            return AutomationResult(
                success=True,
                message=f"已搜索联系人: {contact_name}",
                details={"contact_name": contact_name}
            )
            
        except Exception as e:
            logger.error(f"搜索联系人失败: {e}")
            return AutomationResult(
                success=False,
                message=f"搜索联系人出错: {str(e)}"
            )
    
    def select_contact_from_list(self, window_info, contact_name: str) -> AutomationResult:
        """
        从联系人列表中选择指定联系人

        Args:
            window_info: 窗口信息
            contact_name: 要选择的联系人名称

        Returns:
            AutomationResult: 操作结果
        """
        try:
            from wechat_window import WeChatWindowDetector
            import pyautogui

            detector = WeChatWindowDetector()
            
            # 获取联系人列表区域
            list_area = detector.get_contact_list_area(window_info)
            
            # 模拟按Tab键切换到联系人列表（如果需要）
            self._press_key("tab")
            time.sleep(0.2)
            
            # 尝试查找包含联系人名称的列表项
            # 这个功能需要结合OCR或图像识别，目前返回提示
            logger.info(f"需要选择联系人: {contact_name}")
            
            return AutomationResult(
                success=True,
                message=f"请手动选择联系人: {contact_name}",
                details={"contact_name": contact_name, "note": "自动选择功能需要后续实现"}
            )
            
        except Exception as e:
            logger.error(f"选择联系人失败: {e}")
            return AutomationResult(
                success=False,
                message=f"选择联系人出错: {str(e)}"
            )
    
    def send_message_to_contact(self, window_info, contact_name: str, message: str) -> AutomationResult:
        """
        向指定联系人发送消息

        Args:
            window_info: 窗口信息
            contact_name: 联系人名称
            message: 要发送的消息

        Returns:
            AutomationResult: 操作结果
        """
        results = []
        
        # 1. 搜索联系人
        search_result = self.search_contact(window_info, contact_name)
        results.append(f"搜索联系人: {'成功' if search_result.success else '失败'}")
        
        if not search_result.success:
            return AutomationResult(
                success=False,
                message="发送失败：无法搜索联系人",
                details={"steps": results}
            )
        
        # 2. 选择联系人（需要用户手动确认或后续实现自动选择）
        # 这里我们等待一下让用户看到搜索结果
        time.sleep(1)
        
        # 3. 输入消息
        type_result = self.type_message(message)
        results.append(f"输入消息: {'成功' if type_result.success else '失败'}")
        
        if not type_result.success:
            return AutomationResult(
                success=False,
                message="发送失败：无法输入消息",
                details={"steps": results}
            )
        
        time.sleep(0.2)
        
        # 4. 点击发送
        send_result = self.click_send_button(window_info)
        results.append(f"点击发送: {'成功' if send_result.success else '失败'}")
        
        if send_result.success:
            return AutomationResult(
                success=True,
                message=f"向 {contact_name} 发送消息成功",
                details={
                    "steps": results,
                    "contact": contact_name,
                    "message_length": len(message)
                }
            )
        else:
            # 尝试使用Enter键发送
            if self._press_key("enter"):
                return AutomationResult(
                    success=True,
                    message=f"向 {contact_name} 发送消息成功（使用Enter键）",
                    details={"steps": results + ["使用Enter键发送"], "contact": contact_name}
                )
            
            return AutomationResult(
                success=False,
                message="发送失败：无法点击发送按钮",
                details={"steps": results}
            )

    def type_message(self, message: str, interval: float = 0.05) -> AutomationResult:
        """
        输入文字

        Args:
            message: 要输入的文字
            interval: 每个字符间隔时间

        Returns:
            AutomationResult: 操作结果
        """
        try:
            if not self.pyautogui_available:
                return AutomationResult(
                    success=False,
                    message="PyAutoGUI 不可用"
                )

            import pyautogui
            pyautogui.write(message, interval=interval)

            return AutomationResult(
                success=True,
                message=f"已输入 {len(message)} 个字符",
                details={"char_count": len(message)}
            )

        except Exception as e:
            logger.error(f"输入文字失败: {e}")
            return AutomationResult(
                success=False,
                message=f"输入文字出错: {str(e)}"
            )

    def send_message(self, window_info, message: str) -> AutomationResult:
        """
        发送消息（点击输入框 + 输入文字 + 点击发送）

        Args:
            window_info: 窗口信息
            message: 要发送的消息

        Returns:
            AutomationResult: 操作结果
        """
        results = []
        
        try:
            import pyautogui
            import time
            
            # 调试：检查pyautogui状态
            results.append(f"pyautogui可用: {self.pyautogui_available}")
            results.append(f"当前屏幕大小: {pyautogui.size()}")
            results.append(f"当前鼠标位置: {pyautogui.position()}")
            
            # 0. 确保窗口在前台并激活
            from wechat_window import WeChatWindowDetector
            detector = WeChatWindowDetector()
            
            if hasattr(window_info, 'handle'):
                try:
                    import pywinauto
                    from pywinauto import Application
                    app = Application(backend="uia").connect(handle=window_info.handle)
                    win = app.window(handle=window_info.handle)
                    win.set_focus()
                    win.restore()
                    time.sleep(0.8)  # 增加等待时间
                    results.append("已激活微信窗口")
                except Exception as e:
                    results.append(f"激活窗口失败: {e}")
            
            # 1. 点击输入框（只点击一次）
            input_area = detector.get_input_area(window_info)
            click_x = (input_area[0] + input_area[2]) // 2
            click_y = (input_area[1] + input_area[3]) // 2
            
            results.append(f"输入框区域: {input_area}")
            results.append(f"点击位置: ({click_x}, {click_y})")
            
            # 移动鼠标到位置并点击
            pyautogui.moveTo(click_x, click_y)
            time.sleep(0.2)
            pyautogui.click(click_x, click_y)
            time.sleep(0.5)  # 等待焦点稳定
            
            results.append(f"点击完成，焦点应已稳定")
            
            # 2. 清空输入框
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.15)
            pyautogui.press('delete')
            time.sleep(0.3)
            results.append("清空完成")
            
            # 3. 输入文字（使用剪贴板，对中文最可靠）
            results.append(f"开始输入文字: '{message}'")
            
            # 多次点击确保焦点
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            
            # 清空
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.2)
            
            # 使用剪贴板粘贴（对中文最可靠）
            import pyperclip
            original_clipboard = pyperclip.paste()
            pyperclip.copy(message)
            time.sleep(0.15)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            results.append("剪贴板粘贴完成")
            
            # 恢复原剪贴板内容
            try:
                pyperclip.copy(original_clipboard)
            except:
                pass
            
            # 4. 点击发送按钮
            send_pos = detector.get_send_button_pos(window_info)
            results.append(f"发送按钮位置: {send_pos}")
            
            pyautogui.click(send_pos[0], send_pos[1])
            results.append("点击发送按钮完成")
            
            return AutomationResult(
                success=True,
                message="消息发送成功",
                details={
                    "steps": results,
                    "message_length": len(message),
                    "click_position": (click_x, click_y),
                    "send_position": send_pos
                }
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            import traceback
            traceback.print_exc()
            return AutomationResult(
                success=False,
                message=f"发送失败: {str(e)}",
                details={"steps": results, "error": str(e)}
            )
    
    def send_file(self, window_info, file_path: str) -> AutomationResult:
        """
        发送文件到微信（复制文件 + 粘贴）

        Args:
            window_info: 窗口信息
            file_path: 文件路径

        Returns:
            AutomationResult: 操作结果
        """
        try:
            import pyautogui
            import time
            import os
            import subprocess
            
            results = []
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return AutomationResult(
                    success=False,
                    message=f"文件不存在: {file_path}"
                )
            
            results.append(f"文件路径: {file_path}")
            
            # 获取窗口信息
            from wechat_window import WeChatWindowDetector
            detector = WeChatWindowDetector()
            
            # 1. 点击输入框获取焦点
            input_area = detector.get_input_area(window_info)
            click_x = (input_area[0] + input_area[2]) // 2
            click_y = (input_area[1] + input_area[3]) // 2
            
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)
            results.append("已点击输入框")
            
            # 2. 清空输入框
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.2)
            results.append("已清空输入框")
            
            # 3. 使用 PowerShell 复制文件到剪贴板
            # 使用 Set-Clipboard 命令复制文件
            powershell_cmd = f'powershell -Command "Set-Clipboard -Path \'{file_path}\'"'
            subprocess.run(powershell_cmd, shell=True, capture_output=True)
            time.sleep(0.3)
            results.append("已复制文件到剪贴板")
            
            # 4. 粘贴（Ctrl+V 发送文件）
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            results.append("已粘贴文件")
            
            # 5. 点击发送按钮
            send_pos = detector.get_send_button_pos(window_info)
            pyautogui.click(send_pos[0], send_pos[1])
            time.sleep(0.3)
            results.append("已点击发送按钮")
            
            # 获取文件名
            file_name = os.path.basename(file_path)
            
            return AutomationResult(
                success=True,
                message=f"文件已发送: {file_name}",
                details={
                    "steps": results,
                    "file_path": file_path,
                    "file_name": file_name
                }
            )
            
        except Exception as e:
            logger.error(f"发送文件失败: {e}")
            import traceback
            traceback.print_exc()
            return AutomationResult(
                success=False,
                message=f"发送文件失败: {str(e)}",
                details={"steps": results, "error": str(e)}
            )

    def _click(self, x: int, y: int) -> bool:
        """执行点击"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.click(x, y)
            return True

        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False

    def _double_click(self, x: int, y: int) -> bool:
        """执行双击"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.doubleClick(x, y)
            return True

        except Exception as e:
            logger.error(f"双击失败: {e}")
            return False

    def _right_click(self, x: int, y: int) -> bool:
        """执行右键点击"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.rightClick(x, y)
            return True

        except Exception as e:
            logger.error(f"右键点击失败: {e}")
            return False

    def _move_to(self, x: int, y: int) -> bool:
        """移动鼠标"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.moveTo(x, y)
            return True

        except Exception as e:
            logger.error(f"移动鼠标失败: {e}")
            return False

    def _press_key(self, key: str) -> bool:
        """按下按键"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.press(key)
            return True

        except Exception as e:
            logger.error(f"按键失败: {e}")
            return False

    def _hotkey(self, *keys) -> bool:
        """组合按键"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            pyautogui.hotkey(*keys)
            return True

        except Exception as e:
            logger.error(f"组合按键失败: {e}")
            return False

    def scroll(self, direction: str = "up", clicks: int = 1) -> bool:
        """滚动"""
        try:
            if not self.pyautogui_available:
                return False

            import pyautogui
            scroll_amount = clicks if direction == "up" else -clicks
            pyautogui.scroll(scroll_amount)
            return True

        except Exception as e:
            logger.error(f"滚动失败: {e}")
            return False

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            import pyautogui
            return pyautogui.size()
        except:
            return (1920, 1080)

    def get_current_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置"""
        try:
            import pyautogui
            return pyautogui.position()
        except:
            return (0, 0)


class QuickReplyManager:
    """快捷回复管理器"""

    def __init__(self):
        self.replies = self._load_default_replies()

    def _load_default_replies(self) -> Dict[str, str]:
        """加载默认回复"""
        return {
            "收到": "收到，谢谢！",
            "好的": "好的，明白了！",
            "在吗": "在的，请问有什么事？",
            "谢谢": "不客气！",
            "确认": "已确认收到！",
            "默认": "您好，已收到您的消息，我们会尽快处理。"
        }

    def get_reply(self, keyword: str) -> str:
        """根据关键词获取回复"""
        keyword = keyword.strip()
        return self.replies.get(keyword, self.replies["默认"])

    def add_reply(self, keyword: str, reply: str):
        """添加快捷回复"""
        self.replies[keyword] = reply

    def list_replies(self) -> List[Tuple[str, str]]:
        """列出所有快捷回复"""
        return list(self.replies.items())


def test_automator():
    """测试自动化操作"""
    print("=" * 60)
    print("  微信自动化操作测试")
    print("=" * 60)
    print()

    # 获取窗口信息
    from wechat_window import WeChatWindowDetector

    detector = WeChatWindowDetector()
    window_info = detector.find_wechat_window()

    if not window_info:
        print("❌ 未找到微信窗口，请先打开微信")
        return

    print(f"✅ 找到微信窗口: {window_info.title}")
    print()

    # 创建自动化器
    automator = WeChatAutomator()

    if not automator.pyautogui_available:
        print("❌ PyAutoGUI 不可用")
        return

    # 测试点击输入框
    print("1. 测试点击输入框...")
    result = automator.click_input_box(window_info)
    print(f"   结果: {result.message}")
    time.sleep(0.5)

    # 测试发送消息
    print("\n2. 测试发送消息...")
    test_message = "测试消息 - " + time.strftime("%H:%M:%S")
    result = automator.send_message(window_info, test_message)
    print(f"   结果: {result.message}")
    if result.success:
        print(f"   详情: {result.details}")

    # 测试快捷回复
    print("\n3. 快捷回复管理器:")
    manager = QuickReplyManager()
    for keyword, reply in manager.list_replies()[:3]:
        print(f"   {keyword} -> {reply}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    test_automator()
