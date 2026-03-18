# 自动化执行模块
import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """操作类型"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE = "type"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    MOVE = "move"
    WAIT = "wait"
    PRESS_KEY = "press_key"
    Screenshot = "screenshot"
    FIND_IMAGE = "find_image"


@dataclass
class Action:
    """操作"""
    action_type: ActionType
    target: Optional[str] = None  # 目标位置、图像路径或文本
    x: Optional[int] = None
    y: Optional[int] = None
    duration: float = 0.1  # 操作持续时间
    params: Dict = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


class AutomationExecutor:
    """自动化执行器"""

    def __init__(self):
        self.pyautogui_available = False
        self.keyboard_available = False
        self.mouse_available = False
        self._check_dependencies()
        self.current_position = (0, 0)
        self.action_history: List[Dict] = []
        self._lock = threading.Lock()

    def _check_dependencies(self):
        """检查依赖是否可用"""
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
            logger.info("keyboard 库初始化成功")
        except ImportError:
            logger.warning("keyboard 库未安装")

        try:
            import mouse
            self.mouse_available = True
            logger.info("mouse 库初始化成功")
        except ImportError:
            logger.warning("mouse 库未安装")

    def execute(self, actions: List[Dict]) -> Dict:
        """
        执行一系列操作

        Args:
            actions: 操作列表，每个操作是一个字典

        Returns:
            执行结果
        """
        if not self.pyautogui_available:
            return {
                "success": False,
                "error": "PyAutoGUI 不可用",
                "executed_count": 0
            }

        results = {
            "success": True,
            "executed_count": 0,
            "failed_count": 0,
            "actions": [],
            "error": None
        }

        try:
            import pyautogui

            for action_data in actions:
                try:
                    action_type = action_data.get("action_type", "")
                    action = self._create_action(action_type, action_data)

                    if action is None:
                        results["failed_count"] += 1
                        results["actions"].append({
                            "action": action_data,
                            "success": False,
                            "error": "Unknown action type"
                        })
                        continue

                    # 执行操作
                    success = self._execute_single_action(action, pyautogui)

                    if success:
                        results["executed_count"] += 1
                    else:
                        results["failed_count"] += 1

                    results["actions"].append({
                        "action": action_data,
                        "success": success
                    })

                    time.sleep(action.duration)

                except Exception as e:
                    logger.error(f"操作执行失败: {e}")
                    results["failed_count"] += 1
                    results["actions"].append({
                        "action": action_data,
                        "success": False,
                        "error": str(e)
                    })

            results["success"] = results["failed_count"] == 0

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            logger.error(f"批量操作执行失败: {e}")

        return results

    def _create_action(self, action_type: str, action_data: Dict) -> Optional[Action]:
        """创建Action对象"""
        try:
            action_enum = ActionType(action_type)
            return Action(
                action_type=action_enum,
                target=action_data.get("target"),
                x=action_data.get("x"),
                y=action_data.get("y"),
                duration=action_data.get("duration", 0.1),
                params=action_data.get("params", {})
            )
        except ValueError:
            logger.warning(f"未知的操作类型: {action_type}")
            return None

    def _execute_single_action(self, action: Action, pyautogui) -> bool:
        """执行单个操作"""
        try:
            if action.action_type == ActionType.CLICK:
                x = action.x or 0
                y = action.y or 0
                pyautogui.click(x, y)
                self.current_position = (x, y)

            elif action.action_type == ActionType.DOUBLE_CLICK:
                x = action.x or self.current_position[0]
                y = action.y or self.current_position[1]
                pyautogui.doubleClick(x, y)
                self.current_position = (x, y)

            elif action.action_type == ActionType.RIGHT_CLICK:
                x = action.x or self.current_position[0]
                y = action.y or self.current_position[1]
                pyautogui.rightClick(x, y)
                self.current_position = (x, y)

            elif action.action_type == ActionType.MOVE:
                x = action.x if action.x is not None else self.current_position[0]
                y = action.y if action.y is not None else self.current_position[1]
                pyautogui.moveTo(x, y)
                self.current_position = (x, y)

            elif action.action_type == ActionType.TYPE:
                text = action.target or ""
                pyautogui.write(text, interval=0.05)

            elif action.action_type == ActionType.HOTKEY:
                keys = action.params.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)

            elif action.action_type == ActionType.PRESS_KEY:
                key = action.target or "enter"
                pyautogui.press(key)

            elif action.action_type == ActionType.SCROLL:
                clicks = action.params.get("clicks", 1)
                x = action.x or self.current_position[0]
                y = action.y or self.current_position[1]
                pyautogui.scroll(clicks, x=x, y=y)

            elif action.action_type == ActionType.WAIT:
                duration = action.duration or 1.0
                time.sleep(duration)

            elif action.action_type == ActionType.Screenshot:
                screenshot = pyautogui.screenshot()
                return screenshot

            return True

        except Exception as e:
            logger.error(f"操作执行错误: {e}")
            return False

    def get_screen_size(self) -> tuple:
        """获取屏幕尺寸"""
        if self.pyautogui_available:
            import pyautogui
            return pyautogui.size()
        return (1920, 1080)

    def get_current_position(self) -> tuple:
        """获取当前鼠标位置"""
        if self.pyautogui_available:
            import pyautogui
            return pyautogui.position()
        return (0, 0)

    def click(self, x: int, y: int) -> bool:
        """点击指定位置"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            pyautogui.click(x, y)
            self.current_position = (x, y)
            return True
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """输入文本"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            pyautogui.write(text, interval=0.05)
            return True
        except Exception as e:
            logger.error(f"输入文本失败: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """按下按键"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            pyautogui.press(key)
            return True
        except Exception as e:
            logger.error(f"按键失败: {e}")
            return False

    def hotkey(self, *keys) -> bool:
        """组合按键"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"组合按键失败: {e}")
            return False

    def scroll(self, direction: str = "up", clicks: int = 1) -> bool:
        """滚动鼠标滚轮"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            scroll_amount = clicks if direction == "up" else -clicks
            pyautogui.scroll(scroll_amount)
            return True
        except Exception as e:
            logger.error(f"滚动失败: {e}")
            return False

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int,
             duration: float = 0.5) -> bool:
        """拖拽"""
        if not self.pyautogui_available:
            return False

        try:
            import pyautogui
            pyautogui.moveTo(from_x, from_y)
            pyautogui.dragTo(to_x, to_y, duration=duration)
            self.current_position = (to_x, to_y)
            return True
        except Exception as e:
            logger.error(f"拖拽失败: {e}")
            return False

    def find_image(self, image_path: str, confidence: float = 0.8) -> Optional[tuple]:
        """在屏幕上查找图像"""
        if not self.pyautogui_available:
            return None

        try:
            import pyautogui
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return (center.x, center.y)
            return None
        except Exception as e:
            logger.error(f"图像查找失败: {e}")
            return None

    def take_screenshot(self, region: tuple = None):
        """截取屏幕"""
        if not self.pyautogui_available:
            return None

        try:
            import pyautogui
            if region:
                return pyautogui.screenshot(region=region)
            return pyautogui.screenshot()
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None

    def clear_action_history(self):
        """清除操作历史"""
        with self._lock:
            self.action_history.clear()

    def get_action_history(self) -> List[Dict]:
        """获取操作历史"""
        with self._lock:
            return self.action_history.copy()


class WeChatAutomation:
    """微信自动化操作"""

    def __init__(self, executor: AutomationExecutor = None):
        self.executor = executor or AutomationExecutor()
        self.message_queue = []

    def send_message(self, message: str) -> bool:
        """发送消息"""
        try:
            # 确保微信窗口在最前
            self._ensure_wechat_focused()

            # 输入消息
            self.executor.type_text(message)

            # 发送（Enter键）
            self.executor.press_key("enter")

            return True

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def _ensure_wechat_focused(self):
        """确保微信窗口获得焦点"""
        import pyautogui

        # 尝试查找微信窗口
        try:
            # 使用Alt+Tab切换到微信（如果有多个窗口）
            pyautogui.hotkey("alt", "tab")
            time.sleep(0.5)
        except:
            pass

    def read_latest_messages(self, count: int = 5) -> List[Dict]:
        """读取最新消息"""
        messages = []

        try:
            # 截图并识别
            screenshot = self.executor.take_screenshot()
            if screenshot is None:
                return messages

            # TODO: 使用OCR识别消息内容
            # 这里返回空列表，实际使用时需要OCR支持

        except Exception as e:
            logger.error(f"读取消息失败: {e}")

        return messages

    def reply_message(self, original_message: str, reply: str) -> bool:
        """回复消息"""
        logger.info(f"收到消息: {original_message}")
        logger.info(f"回复: {reply}")
        return self.send_message(reply)

    def send_file(self, file_path: str) -> bool:
        """发送文件"""
        try:
            import pyautogui

            # 打开文件选择对话框
            self.executor.press_key("ctrl", "o")
            time.sleep(0.5)

            # 输入文件路径
            self.executor.type_text(file_path)
            time.sleep(0.5)

            # 确认发送
            self.executor.press_key("enter")

            return True

        except Exception as e:
            logger.error(f"发送文件失败: {e}")
            return False


class ExcelAutomation:
    """Excel自动化操作"""

    def __init__(self, executor: AutomationExecutor = None):
        self.executor = executor or AutomationExecutor()

    def open_excel(self, file_path: str) -> bool:
        """打开Excel文件"""
        try:
            import pyautogui

            # 使用Win+R打开文件
            pyautogui.hotkey("win", "r")
            time.sleep(0.5)

            self.executor.type_text(file_path)
            time.sleep(0.5)

            self.executor.press_key("enter")
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f"打开Excel失败: {e}")
            return False

    def fill_cell(self, cell: str, value: str) -> bool:
        """填充单元格"""
        try:
            import pyautogui

            # 选中单元格
            for char in cell:
                self.executor.type_text(char)
                time.sleep(0.05)

            self.executor.press_key("right")
            self.executor.type_text(value)

            return True

        except Exception as e:
            logger.error(f"填充单元格失败: {e}")
            return False

    def save_workbook(self) -> bool:
        """保存工作簿"""
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "s")
            time.sleep(0.5)
            self.executor.press_key("enter")
            return True
        except Exception as e:
            logger.error(f"保存工作簿失败: {e}")
            return False

    def close_excel(self) -> bool:
        """关闭Excel"""
        try:
            import pyautogui
            pyautogui.hotkey("alt", "f4")
            time.sleep(0.5)
            # 忽略未保存的提示
            self.executor.press_key("n")
            return True
        except Exception as e:
            logger.error(f"关闭Excel失败: {e}")
            return False
