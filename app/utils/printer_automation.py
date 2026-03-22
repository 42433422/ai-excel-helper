import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple

import win32api
import win32con
import win32gui
import win32print

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PrinterAutomation:
    def __init__(self):
        self.current_printer = None
        self.original_default = None

    def move_mouse(self, x: int, y: int):
        win32api.SetCursorPos((x, y))
        time.sleep(0.2)

    def click_mouse(self, x: int, y: int, button: str = 'left'):
        self.move_mouse(x, y)

        if button == 'left':
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == 'right':
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        time.sleep(0.3)

    def find_window(self, title: str) -> int:
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title in window_title:
                    hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else 0

    def get_window_position(self, hwnd: int) -> Tuple[int, int, int, int]:
        rect = win32gui.GetWindowRect(hwnd)
        return rect

    def set_default_printer(self, printer_name: str) -> bool:
        try:
            logger.info(f"设置Windows默认打印机为: {printer_name}")

            result = subprocess.run([
                'rundll32', 'printui.dll,PrintUIEntry',
                '/y', '/n', printer_name
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"成功设置默认打印机为: {printer_name}")
                time.sleep(1)
                return True
            else:
                logger.error(f"设置默认打印机失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"设置默认打印机异常: {e}")
            return False

    def handle_printer_dialog(self, target_printer: str, timeout: int = 10) -> bool:
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            hwnd = self.find_window('打印')
            if hwnd:
                logger.info(f"找到打印机对话框，窗口句柄: {hwnd}")

                rect = self.get_window_position(hwnd)
                logger.info(f"对话框位置: {rect}")

                center_x = (rect[0] + rect[2]) // 2
                center_y = (rect[1] + rect[3]) // 2

                printer_dropdown_x = center_x
                printer_dropdown_y = center_y - 100
                self.click_mouse(printer_dropdown_x, printer_dropdown_y)

                time.sleep(0.5)

                logger.info(f"尝试选择打印机: {target_printer}")

                ok_button_x = center_x + 100
                ok_button_y = center_y + 50
                self.click_mouse(ok_button_x, ok_button_y)

                logger.info("打印机对话框处理完成")
                return True

            time.sleep(0.5)

        logger.info("未找到打印机对话框")
        return False

    def print_with_automation(self, file_path: str, target_printer: str) -> Dict:
        try:
            logger.info(f"开始自动化打印: {file_path} 到 {target_printer}")

            self.original_default = win32print.GetDefaultPrinter()
            logger.info(f"原始默认打印机: {self.original_default}")

            if self.original_default != target_printer:
                logger.info(f"临时设置默认打印机为: {target_printer}")
                self.set_default_printer(target_printer)

            logger.info("使用ShellExecute打印文件")
            result = win32api.ShellExecute(
                0,
                "print",
                file_path,
                f'/d:"{target_printer}"',
                ".",
                1
            )

            if result <= 32:
                raise Exception(f"ShellExecute失败，错误代码: {result}")

            logger.info(f"ShellExecute调用成功，结果: {result}")

            logger.info("检查是否需要处理打印机对话框...")
            self.handle_printer_dialog(target_printer)

            logger.info("等待打印完成...")
            time.sleep(5)

            if self.original_default and self.original_default != target_printer:
                logger.info(f"恢复原始默认打印机: {self.original_default}")
                self.set_default_printer(self.original_default)

            return {
                "success": True,
                "message": f"自动化打印成功发送到 {target_printer}",
                "printer": target_printer,
                "file": file_path
            }

        except Exception as e:
            logger.error(f"自动化打印失败: {e}")

            if self.original_default and self.current_printer != self.original_default:
                try:
                    self.set_default_printer(self.original_default)
                except:
                    pass

            return {
                "success": False,
                "message": f"自动化打印失败: {str(e)}"
            }


class EnhancedPrinterUtils:
    def __init__(self):
        self.automation = PrinterAutomation()

    def print_file_enhanced(self, file_path: str, printer_name: str, use_automation: bool = True, use_default_printer: bool = False) -> Dict:
        try:
            if not use_automation:
                from app.utils.print_utils import PrinterUtils
                utils = PrinterUtils()
                return utils.print_file(file_path, printer_name, use_default_printer=use_default_printer)
            else:
                return self.automation.print_with_automation(file_path, printer_name)

        except Exception as e:
            logger.error(f"增强打印失败: {e}")
            return {
                "success": False,
                "message": f"增强打印失败: {str(e)}"
            }
