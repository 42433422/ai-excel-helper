import unittest
from unittest.mock import Mock, MagicMock, patch
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class TestPrinterAutomation(unittest.TestCase):

    def setUp(self):
        pass

    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.time')
    def test_move_mouse(self, mock_time, mock_win32api):
        from app.utils.printer_automation import PrinterAutomation

        automation = PrinterAutomation()
        automation.move_mouse(100, 200)

        mock_win32api.SetCursorPos.assert_called_once_with((100, 200))
        mock_time.sleep.assert_called()

    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.win32con')
    @patch('app.utils.printer_automation.time')
    def test_click_mouse_left(self, mock_time, mock_win32con, mock_win32api):
        from app.utils.printer_automation import PrinterAutomation

        automation = PrinterAutomation()
        automation.click_mouse(100, 200, button='left')

        mock_win32api.SetCursorPos.assert_called_once_with((100, 200))
        mock_win32api.mouse_event.assert_called()
        self.assertEqual(mock_win32api.mouse_event.call_count, 2)
        mock_time.sleep.assert_called()

    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.win32con')
    @patch('app.utils.printer_automation.time')
    def test_click_mouse_right(self, mock_time, mock_win32con, mock_win32api):
        from app.utils.printer_automation import PrinterAutomation

        automation = PrinterAutomation()
        automation.click_mouse(100, 200, button='right')

        mock_win32api.SetCursorPos.assert_called_once_with((100, 200))
        mock_win32api.mouse_event.assert_called()
        self.assertEqual(mock_win32api.mouse_event.call_count, 2)

    @patch('app.utils.printer_automation.win32gui')
    def test_find_window_found(self, mock_win32gui):
        from app.utils.printer_automation import PrinterAutomation

        mock_hwnd1 = Mock()

        mock_win32gui.IsWindowVisible.return_value = True
        mock_win32gui.GetWindowText.return_value = "打印对话框"

        def callback(hwnd, hwnds):
            if mock_win32gui.IsWindowVisible(hwnd):
                window_title = mock_win32gui.GetWindowText(hwnd)
                if "打印" in window_title:
                    hwnds.append(hwnd)
            return True

        mock_win32gui.EnumWindows.side_effect = lambda cb, arg: cb(mock_hwnd1, arg)

        automation = PrinterAutomation()
        result = automation.find_window("打印")

        self.assertEqual(result, mock_hwnd1)

    @patch('app.utils.printer_automation.win32gui')
    def test_find_window_not_found(self, mock_win32gui):
        from app.utils.printer_automation import PrinterAutomation

        mock_win32gui.IsWindowVisible.return_value = False

        automation = PrinterAutomation()
        result = automation.find_window("不存在")

        self.assertEqual(result, 0)

    @patch('app.utils.printer_automation.win32gui')
    def test_get_window_position(self, mock_win32gui):
        from app.utils.printer_automation import PrinterAutomation

        mock_win32gui.GetWindowRect.return_value = (0, 0, 800, 600)

        automation = PrinterAutomation()
        result = automation.get_window_position(12345)

        self.assertEqual(result, (0, 0, 800, 600))
        mock_win32gui.GetWindowRect.assert_called_once_with(12345)

    @patch('app.utils.printer_automation.subprocess')
    @patch('app.utils.printer_automation.time')
    def test_set_default_printer_success(self, mock_time, mock_subprocess):
        from app.utils.printer_automation import PrinterAutomation

        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.run.return_value = mock_result

        automation = PrinterAutomation()
        result = automation.set_default_printer("Test Printer")

        self.assertTrue(result)
        mock_subprocess.run.assert_called_once()
        mock_time.sleep.assert_called()

    @patch('app.utils.printer_automation.subprocess')
    @patch('app.utils.printer_automation.time')
    def test_set_default_printer_failure(self, mock_time, mock_subprocess):
        from app.utils.printer_automation import PrinterAutomation

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "错误信息"
        mock_subprocess.run.return_value = mock_result

        automation = PrinterAutomation()
        result = automation.set_default_printer("Test Printer")

        self.assertFalse(result)

    @patch('app.utils.printer_automation.subprocess')
    @patch('app.utils.printer_automation.time')
    def test_set_default_printer_exception(self, mock_time, mock_subprocess):
        from app.utils.printer_automation import PrinterAutomation

        mock_subprocess.run.side_effect = Exception("执行异常")

        automation = PrinterAutomation()
        result = automation.set_default_printer("Test Printer")

        self.assertFalse(result)

    @patch('app.utils.printer_automation.time')
    @patch('app.utils.printer_automation.PrinterAutomation.find_window')
    @patch('app.utils.printer_automation.PrinterAutomation.get_window_position')
    @patch('app.utils.printer_automation.PrinterAutomation.click_mouse')
    def test_handle_printer_dialog_found(self, mock_click, mock_get_pos, mock_find, mock_time):
        from app.utils.printer_automation import PrinterAutomation

        mock_find.return_value = 12345
        mock_get_pos.return_value = (0, 0, 800, 600)

        mock_time.time.return_value = 0

        automation = PrinterAutomation()
        result = automation.handle_printer_dialog("Test Printer", timeout=1)

        self.assertTrue(result)
        mock_click.assert_called()

    @patch('app.utils.printer_automation.PrinterAutomation.find_window')
    @patch('app.utils.printer_automation.PrinterAutomation.get_window_position')
    @patch('app.utils.printer_automation.time')
    def test_handle_printer_dialog_not_found(self, mock_time, mock_get_pos, mock_find):
        from app.utils.printer_automation import PrinterAutomation

        mock_find.return_value = 0

        def side_effect(*args):
            import time
            time.sleep(0.01)

        mock_time.time.side_effect = [0, 0, 1.5, 1.5]

        automation = PrinterAutomation()
        result = automation.handle_printer_dialog("Test Printer", timeout=1)

        self.assertFalse(result)

    @patch('app.utils.printer_automation.win32print')
    @patch('app.utils.printer_automation.PrinterAutomation.set_default_printer')
    @patch('app.utils.printer_automation.PrinterAutomation.handle_printer_dialog')
    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.time')
    def test_print_with_automation_success(self, mock_time, mock_shell, mock_handle, mock_set, mock_win32print):
        from app.utils.printer_automation import PrinterAutomation

        mock_win32print.GetDefaultPrinter.return_value = "Original Printer"
        mock_shell.ShellExecute.return_value = 33
        mock_set.return_value = True
        mock_handle.return_value = True

        automation = PrinterAutomation()
        result = automation.print_with_automation("test.pdf", "Test Printer")

        self.assertTrue(result['success'])
        self.assertEqual(result['printer'], "Test Printer")
        self.assertEqual(result['file'], "test.pdf")

    @patch('app.utils.printer_automation.win32print')
    @patch('app.utils.printer_automation.PrinterAutomation.set_default_printer')
    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.time')
    def test_print_with_automation_shell_execute_failure(self, mock_time, mock_shell, mock_set, mock_win32print):
        from app.utils.printer_automation import PrinterAutomation

        mock_win32print.GetDefaultPrinter.return_value = "Original Printer"
        mock_shell.ShellExecute.return_value = 0

        automation = PrinterAutomation()
        result = automation.print_with_automation("test.pdf", "Test Printer")

        self.assertFalse(result['success'])
        self.assertIn('ShellExecute失败', result['message'])

    @patch('app.utils.printer_automation.win32print')
    @patch('app.utils.printer_automation.PrinterAutomation.set_default_printer')
    @patch('app.utils.printer_automation.PrinterAutomation.handle_printer_dialog')
    @patch('app.utils.printer_automation.win32api')
    @patch('app.utils.printer_automation.time')
    def test_print_with_automation_exception(self, mock_time, mock_shell, mock_handle, mock_set, mock_win32print):
        from app.utils.printer_automation import PrinterAutomation

        mock_win32print.GetDefaultPrinter.side_effect = Exception("获取打印机异常")

        automation = PrinterAutomation()
        result = automation.print_with_automation("test.pdf", "Test Printer")

        self.assertFalse(result['success'])


class TestEnhancedPrinterUtils(unittest.TestCase):

    def setUp(self):
        pass

    @patch('app.utils.printer_automation.PrinterAutomation')
    def test_enhanced_printer_utils_init(self, mock_automation):
        from app.utils.printer_automation import EnhancedPrinterUtils

        utils = EnhancedPrinterUtils()

        mock_automation.assert_called_once()
        self.assertIsNotNone(utils.automation)

    @patch('app.utils.printer_automation.PrinterAutomation')
    def test_print_file_enhanced_with_automation(self, mock_automation):
        from app.utils.printer_automation import EnhancedPrinterUtils

        mock_automation_instance = MagicMock()
        mock_automation.return_value = mock_automation_instance
        mock_automation_instance.print_with_automation.return_value = {
            "success": True,
            "message": "打印成功"
        }

        utils = EnhancedPrinterUtils()
        result = utils.print_file_enhanced("test.pdf", "Test Printer", use_automation=True)

        self.assertTrue(result['success'])
        mock_automation_instance.print_with_automation.assert_called_once_with("test.pdf", "Test Printer")

    @patch('app.utils.printer_automation.PrinterAutomation')
    @patch('app.utils.print_utils.PrinterUtils')
    def test_print_file_enhanced_without_automation(self, mock_printer_utils_class, mock_automation):
        from app.utils.printer_automation import EnhancedPrinterUtils

        mock_automation_instance = MagicMock()
        mock_automation.return_value = mock_automation_instance

        mock_printer_utils_instance = MagicMock()
        mock_printer_utils_class.return_value = mock_printer_utils_instance
        mock_printer_utils_instance.print_file.return_value = {"success": True, "message": "普通打印成功"}

        utils = EnhancedPrinterUtils()
        result = utils.print_file_enhanced("test.pdf", "Test Printer", use_automation=False)

        self.assertTrue(result['success'])
        mock_printer_utils_instance.print_file.assert_called_once()

    @patch('app.utils.printer_automation.PrinterAutomation')
    def test_print_file_enhanced_exception(self, mock_automation):
        from app.utils.printer_automation import EnhancedPrinterUtils

        mock_automation_instance = MagicMock()
        mock_automation.return_value = mock_automation_instance
        mock_automation_instance.print_with_automation.side_effect = Exception("打印异常")

        utils = EnhancedPrinterUtils()
        result = utils.print_file_enhanced("test.pdf", "Test Printer", use_automation=True)

        self.assertFalse(result['success'])
        self.assertIn('打印异常', result['message'])


class TestPrinterAutomationModuleImport(unittest.TestCase):

    def test_printer_automation_import(self):
        try:
            from app.utils.printer_automation import PrinterAutomation
            self.assertIsNotNone(PrinterAutomation)
        except ImportError as e:
            self.fail(f"导入 PrinterAutomation 失败: {e}")

    def test_enhanced_printer_utils_import(self):
        try:
            from app.utils.printer_automation import EnhancedPrinterUtils
            self.assertIsNotNone(EnhancedPrinterUtils)
        except ImportError as e:
            self.fail(f"导入 EnhancedPrinterUtils 失败: {e}")


if __name__ == '__main__':
    unittest.main()
