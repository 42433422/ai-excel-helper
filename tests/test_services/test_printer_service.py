import unittest
from unittest.mock import Mock, MagicMock, patch
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class TestPrinterService(unittest.TestCase):

    def setUp(self):
        self.mock_printer_utils = MagicMock()
        self.mock_enhanced_utils = MagicMock()

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_get_printers_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_available_printers.return_value = [
            {"name": "Printer1", "status": "就绪", "is_default": True},
            {"name": "Printer2", "status": "打印中", "is_default": False}
        ]

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.get_printers()

        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['printers']), 2)
        mock_printer_instance.get_available_printers.assert_called_once()

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_get_printers_exception(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_available_printers.side_effect = Exception("获取打印机失败")

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.get_printers()

        self.assertFalse(result['success'])
        self.assertIn('message', result)
        self.assertEqual(result['printers'], [])

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_get_default_printer_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = "Default Printer"

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.get_default_printer()

        self.assertTrue(result['success'])
        self.assertEqual(result['printer'], "Default Printer")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_get_default_printer_not_found(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = None

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.get_default_printer()

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], "未找到默认打印机")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_get_default_printer_exception(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.side_effect = Exception("获取默认打印机异常")

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.get_default_printer()

        self.assertFalse(result['success'])
        self.assertIn('message', result)

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_document_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = "Test Printer"
        mock_printer_instance.print_file.return_value = {"success": True, "message": "打印成功"}

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_document("test.pdf", printer_name="Test Printer")

        self.assertTrue(result['success'])
        mock_printer_instance.print_file.assert_called_once()

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_document_no_printer_specified(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = None

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_document("test.pdf")

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], "未指定打印机且无法获取默认打印机")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_document_printer_failed(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = "Test Printer"
        mock_printer_instance.print_file.return_value = {"success": False, "message": "打印机失败"}

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_document("test.pdf", printer_name="Test Printer")

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], "打印机失败")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_document_with_automation(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_default_printer.return_value = "Test Printer"

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance
        mock_enhanced_instance.print_file_enhanced.return_value = {"success": True, "message": "增强打印成功"}

        service = PrinterService()
        result = service.print_document("test.pdf", printer_name="Test Printer", use_automation=True)

        self.assertTrue(result['success'])
        mock_enhanced_instance.print_file_enhanced.assert_called_once()

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_label_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_label_printer.return_value = "Label Printer"
        mock_printer_instance.print_file.return_value = {"success": True, "message": "打印成功"}

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_label("label.pdf")

        self.assertTrue(result['success'])
        self.assertEqual(result['printer'], "Label Printer")
        self.assertEqual(result['copies'], 1)
        self.assertEqual(result['successful'], 1)

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_label_no_label_printer(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_label_printer.return_value = None

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_label("label.pdf")

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], "未找到标签打印机")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_label_multiple_copies(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_label_printer.return_value = "Label Printer"
        mock_printer_instance.print_file.return_value = {"success": True, "message": "打印成功"}

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_label("label.pdf", copies=3)

        self.assertTrue(result['success'])
        self.assertEqual(result['copies'], 3)
        self.assertEqual(result['successful'], 3)
        self.assertEqual(mock_printer_instance.print_file.call_count, 3)

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_label_with_printer_name(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.print_file.return_value = {"success": True, "message": "打印成功"}

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_label("label.pdf", printer_name="Custom Label Printer", copies=2)

        self.assertTrue(result['success'])
        self.assertEqual(result['printer'], "Custom Label Printer")
        self.assertEqual(result['copies'], 2)

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_print_label_partial_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_label_printer.return_value = "Label Printer"

        results = [
            {"success": True, "message": "打印成功"},
            {"success": False, "message": "打印失败"},
            {"success": True, "message": "打印成功"}
        ]
        mock_printer_instance.print_file.side_effect = results

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.print_label("label.pdf", copies=3)

        self.assertTrue(result['success'])
        self.assertEqual(result['successful'], 2)

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_test_printer_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.test_printer.return_value = {
            "success": True,
            "available": True,
            "printer": "Test Printer",
            "status": "就绪"
        }

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.test_printer("Test Printer")

        self.assertTrue(result['success'])
        self.assertTrue(result['available'])
        self.assertEqual(result['printer'], "Test Printer")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_test_printer_failure(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.test_printer.return_value = {
            "success": False,
            "available": False,
            "printer": "Test Printer",
            "message": "打印机不可用"
        }

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.test_printer("Test Printer")

        self.assertFalse(result['success'])
        self.assertFalse(result['available'])

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_test_printer_exception(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.test_printer.side_effect = Exception("测试打印机异常")

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.test_printer("Test Printer")

        self.assertFalse(result['success'])
        self.assertFalse(result['available'])

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_validate_printer_separation_success(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_document_printer.return_value = "Document Printer"
        mock_printer_instance.get_label_printer.return_value = "Label Printer"

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.validate_printer_separation()

        self.assertTrue(result['valid'])
        self.assertEqual(result['doc_printer'], "Document Printer")
        self.assertEqual(result['label_printer'], "Label Printer")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_validate_printer_separation_same_printer(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_document_printer.return_value = "Same Printer"
        mock_printer_instance.get_label_printer.return_value = "Same Printer"

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.validate_printer_separation()

        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], "发货单打印机和标签打印机相同")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_validate_printer_separation_missing_doc_printer(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_document_printer.return_value = None
        mock_printer_instance.get_label_printer.return_value = "Label Printer"

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.validate_printer_separation()

        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], "无法识别发货单或标签打印机")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_validate_printer_separation_missing_label_printer(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_document_printer.return_value = "Document Printer"
        mock_printer_instance.get_label_printer.return_value = None

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.validate_printer_separation()

        self.assertFalse(result['valid'])
        self.assertEqual(result['error'], "无法识别发货单或标签打印机")

    @patch('app.services.printer_service.PrinterUtils')
    @patch('app.services.printer_service.EnhancedPrinterUtils')
    def test_validate_printer_separation_exception(self, mock_enhanced, mock_printer):
        from app.services.printer_service import PrinterService

        mock_printer_instance = MagicMock()
        mock_printer.return_value = mock_printer_instance
        mock_printer_instance.get_document_printer.side_effect = Exception("验证异常")

        mock_enhanced_instance = MagicMock()
        mock_enhanced.return_value = mock_enhanced_instance

        service = PrinterService()
        result = service.validate_printer_separation()

        self.assertFalse(result['valid'])
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
