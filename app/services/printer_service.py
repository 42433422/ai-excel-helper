import logging
import os
from typing import Dict, List, Optional

from app.utils.print_utils import PrinterUtils
from app.utils.printer_automation import EnhancedPrinterUtils

logger = logging.getLogger(__name__)


class PrinterService:
    def __init__(self):
        self.printer_utils = PrinterUtils()
        self.enhanced_utils = EnhancedPrinterUtils()

    def get_printers(self) -> Dict:
        try:
            printers = self.printer_utils.get_available_printers()
            return {
                "success": True,
                "printers": printers,
                "count": len(printers)
            }
        except Exception as e:
            logger.error(f"获取打印机列表失败: {e}")
            return {
                "success": False,
                "message": str(e),
                "printers": []
            }

    def get_default_printer(self) -> Dict:
        try:
            printer = self.printer_utils.get_default_printer()
            if printer:
                return {
                    "success": True,
                    "printer": printer
                }
            else:
                return {
                    "success": False,
                    "message": "未找到默认打印机"
                }
        except Exception as e:
            logger.error(f"获取默认打印机失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def get_document_printer(self) -> Optional[str]:
        return self.printer_utils.get_document_printer()

    def get_label_printer(self) -> Optional[str]:
        return self.printer_utils.get_label_printer()

    def print_document(self, file_path: str, printer_name: Optional[str] = None, use_automation: bool = False) -> Dict:
        try:
            if not printer_name:
                printer_name = self.printer_utils.get_default_printer()

            if not printer_name:
                return {
                    "success": False,
                    "message": "未指定打印机且无法获取默认打印机"
                }

            if use_automation:
                return self.enhanced_utils.print_file_enhanced(
                    file_path,
                    printer_name,
                    use_automation=True
                )
            else:
                return self.printer_utils.print_file(
                    file_path,
                    printer_name,
                    use_default_printer=False
                )
        except Exception as e:
            logger.error(f"打印文档失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def print_label(self, file_path: str, printer_name: Optional[str] = None, copies: int = 1) -> Dict:
        try:
            if not printer_name:
                printer_name = self.get_label_printer()

            if not printer_name:
                return {
                    "success": False,
                    "message": "未找到标签打印机"
                }

            results = []
            for i in range(copies):
                result = self.printer_utils.print_file(file_path, printer_name)
                results.append({
                    "copy": i + 1,
                    "result": result
                })

            success_count = sum(1 for r in results if r['result'].get('success', False))

            return {
                "success": success_count > 0,
                "message": f"标签打印完成: {success_count}/{copies} 成功",
                "printer": printer_name,
                "copies": copies,
                "successful": success_count,
                "details": results
            }
        except Exception as e:
            logger.error(f"打印标签失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def test_printer(self, printer_name: str) -> Dict:
        try:
            return self.printer_utils.test_printer(printer_name)
        except Exception as e:
            logger.error(f"测试打印机失败: {e}")
            return {
                "success": False,
                "available": False,
                "printer": printer_name,
                "message": str(e)
            }

    def validate_printer_separation(self) -> Dict:
        try:
            doc_printer = self.get_document_printer()
            label_printer = self.get_label_printer()

            if not doc_printer or not label_printer:
                return {
                    "valid": False,
                    "error": "无法识别发货单或标签打印机",
                    "doc_printer": doc_printer,
                    "label_printer": label_printer
                }

            if doc_printer == label_printer:
                return {
                    "valid": False,
                    "error": "发货单打印机和标签打印机相同",
                    "doc_printer": doc_printer,
                    "label_printer": label_printer
                }

            return {
                "valid": True,
                "doc_printer": doc_printer,
                "label_printer": label_printer
            }
        except Exception as e:
            logger.error(f"验证打印机分离失败: {e}")
            return {
                "valid": False,
                "error": str(e)
            }


printer_service = PrinterService()


def get_printers() -> List[Dict]:
    result = printer_service.get_printers()
    return result.get("printers", [])


def get_document_printer() -> Optional[str]:
    return printer_service.get_document_printer()


def get_label_printer() -> Optional[str]:
    return printer_service.get_label_printer()


def validate_printer_separation() -> Dict:
    return printer_service.validate_printer_separation()
