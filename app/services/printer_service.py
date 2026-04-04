import json
import logging
import os
from typing import Dict, List, Optional

from app.utils.print_utils import PrinterUtils
from app.utils.printer_automation import EnhancedPrinterUtils
from app.utils.path_utils import get_app_data_dir

logger = logging.getLogger(__name__)


class PrinterService:
    def __init__(self):
        self.printer_utils = PrinterUtils()
        self.enhanced_utils = EnhancedPrinterUtils()
        config_dir = os.path.join(get_app_data_dir(), "config")
        os.makedirs(config_dir, exist_ok=True)
        self._selection_file = os.path.join(config_dir, "printer_selection.json")

    def _load_selection(self) -> Dict:
        try:
            if not os.path.exists(self._selection_file):
                return {}
            with open(self._selection_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning(f"读取打印机配置失败: {e}")
            return {}

    def _save_selection(self, payload: Dict) -> None:
        with open(self._selection_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _normalize_name(value: Optional[str]) -> str:
        return (value or "").strip()

    @staticmethod
    def _resolve_name(target_name: Optional[str], printers: List[Dict]) -> Optional[str]:
        name = (target_name or "").strip()
        if not name:
            return None
        exact = next((p.get("name") for p in printers if p.get("name") == name), None)
        if exact:
            return exact
        name_lower = name.lower()
        for p in printers:
            p_name = (p.get("name") or "").strip()
            if p_name.lower() == name_lower:
                return p_name
        return None

    @staticmethod
    def _guess_document_printer(printers: List[Dict]) -> Optional[str]:
        if not printers:
            return None
        keywords = ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式', 'hp', 'canon', 'epson']
        for printer in printers:
            name = (printer.get("name") or "").lower()
            if any(kw in name for kw in keywords):
                return printer.get("name")
        return printers[0].get("name")

    @staticmethod
    def _guess_label_printer(printers: List[Dict]) -> Optional[str]:
        if not printers:
            return None
        keywords = ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', 'zebra']
        for printer in printers:
            name = (printer.get("name") or "").lower()
            if any(kw in name for kw in keywords):
                return printer.get("name")
        return printers[-1].get("name")

    def get_printer_selection(self) -> Dict:
        data = self._load_selection()
        return {
            "document_printer": self._normalize_name(data.get("document_printer")) or None,
            "label_printer": self._normalize_name(data.get("label_printer")) or None,
        }

    def save_printer_selection(self, document_printer: Optional[str], label_printer: Optional[str]) -> Dict:
        payload = {
            "document_printer": self._normalize_name(document_printer),
            "label_printer": self._normalize_name(label_printer),
        }
        self._save_selection(payload)
        return {
            "success": True,
            "selection": {
                "document_printer": payload["document_printer"] or None,
                "label_printer": payload["label_printer"] or None,
            },
            "message": "打印机选择已保存",
        }

    def classify_printers(self, printers: List[Dict]) -> Dict:
        selection = self.get_printer_selection()
        selected_doc = self._resolve_name(selection.get("document_printer"), printers)
        selected_label = self._resolve_name(selection.get("label_printer"), printers)

        if selected_doc is None:
            selected_doc = self._guess_document_printer(printers)
        if selected_label is None:
            selected_label = self._guess_label_printer(printers)

        def status_of(name: Optional[str]) -> str:
            if not name:
                return "未连接"
            match = next((p for p in printers if p.get("name") == name), None)
            return (match or {}).get("status") or "未知"

        classified = {
            "document_printer": {
                "name": selected_doc,
                "status": status_of(selected_doc),
                "is_connected": bool(selected_doc),
            },
            "label_printer": {
                "name": selected_label,
                "status": status_of(selected_label),
                "is_connected": bool(selected_label),
            },
        }
        summary = {
            "total_printers": len(printers),
            "document_printer_ready": bool(selected_doc),
            "label_printer_ready": bool(selected_label),
            "all_ready": bool(selected_doc) and bool(selected_label),
        }
        return {
            "classified": classified,
            "summary": summary,
            "selection": {
                "document_printer": selection.get("document_printer"),
                "label_printer": selection.get("label_printer"),
            },
        }

    def get_printers(self) -> Dict:
        try:
            printers = self.printer_utils.get_available_printers()
            classified_info = self.classify_printers(printers)
            return {
                "success": True,
                "printers": printers,
                "count": len(printers),
                **classified_info,
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
        printers = self.printer_utils.get_available_printers()
        if not printers:
            return None
        selection = self.get_printer_selection()
        preferred = self._resolve_name(selection.get("document_printer"), printers)
        return preferred or self._guess_document_printer(printers)

    def get_label_printer(self) -> Optional[str]:
        printers = self.printer_utils.get_available_printers()
        if not printers:
            return None
        selection = self.get_printer_selection()
        preferred = self._resolve_name(selection.get("label_printer"), printers)
        return preferred or self._guess_label_printer(printers)

    def print_document(self, file_path: str, printer_name: Optional[str] = None, use_automation: bool = False) -> Dict:
        try:
            if not printer_name:
                printer_name = self.get_document_printer() or self.printer_utils.get_default_printer()

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
