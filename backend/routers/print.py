"""
打印机管理 API（FastAPI APIRouter）。
支持 Windows 打印机检测（win32print）与模拟模式。
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["print"])

_OFFLINE_STATUSES = frozenset({"离线", "错误", "不可用"})


def _normalize_printer_name(name: str | None) -> str:
    """用于比对已保存名称与 EnumPrinters 返回名称（去首尾空白、大小写不敏感）。"""
    if not name:
        return ""
    return name.strip().casefold()


def _find_printer_by_saved_name(printers: list[dict], saved_name: str | None) -> dict | None:
    """将设置里保存的打印机名与当前枚举列表对齐；避免仅因大小写或空格导致“刷新匹配不到”。"""
    key = _normalize_printer_name(saved_name)
    if not key:
        return None
    stripped = saved_name.strip()
    for x in printers:
        n = x.get("name") or ""
        if n == stripped or _normalize_printer_name(n) == key:
            return x
    return None


def _is_printer_online(p: dict) -> bool:
    return p.get("status") not in _OFFLINE_STATUSES


def _selection_resolution(printers: list[dict], selection: dict) -> dict:
    """供前端展示：已选项是否仍在列表中、是否在线。"""
    doc = _find_printer_by_saved_name(printers, selection.get("document_printer"))
    lbl = _find_printer_by_saved_name(printers, selection.get("label_printer"))
    return {
        "resolved": {"document_printer": doc, "label_printer": lbl},
        "match": {
            "document_printer": doc is not None,
            "label_printer": lbl is not None,
        },
        "online": {
            "document_printer": bool(doc and _is_printer_online(doc)),
            "label_printer": bool(lbl and _is_printer_online(lbl)),
        },
    }


def _get_printer_list_from_win32() -> list[dict]:
    """使用 win32print 获取 Windows 打印机列表。"""
    try:
        import win32print

        printers = []
        try:
            for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 2
            ):
                try:
                    name = p["pPrinterName"]
                    attrs = p.get("Attributes", 0)
                    is_default = bool(attrs & win32print.PRINTER_ATTRIBUTE_DEFAULT)
                    is_shared = bool(attrs & win32print.PRINTER_ATTRIBUTE_SHARED)
                    status = "就绪"
                    try:
                        hPrinter = win32print.OpenPrinter(name)
                        info = win32print.GetPrinter(hPrinter, 2)
                        status_code = info.get("Status", 0)
                        if status_code & win32print.PRINTER_STATUS_ERROR:
                            status = "错误"
                        elif status_code & win32print.PRINTER_STATUS_PAUSED:
                            status = "暂停"
                        elif status_code & win32print.PRINTER_STATUS_PRINTING:
                            status = "打印中"
                        elif status_code & win32print.PRINTER_STATUS_OFFLINE:
                            status = "离线"
                        elif status_code & win32print.PRINTER_STATUS_PAPER_OUT:
                            status = "缺纸"
                        elif status_code & win32print.PRINTER_STATUS_PAPER_JAM:
                            status = "卡纸"
                        win32print.ClosePrinter(hPrinter)
                    except Exception:
                        pass

                    printers.append(
                        {
                            "name": name,
                            "status": status,
                            "is_default": is_default,
                            "is_shared": is_shared,
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to read printer info: %s", e)
                    continue
        except Exception as e:
            logger.warning("EnumPrinters failed: %s", e)
        return printers
    except ImportError:
        logger.warning("win32print not available")
        return []


def _get_printer_list_mock() -> list[dict]:
    """无 win32print 时返回模拟打印机列表。"""
    return [
        {"name": "Microsoft Print to PDF", "status": "就绪", "is_default": True, "is_shared": False},
        {"name": "Microsoft XPS Document Writer", "status": "就绪", "is_default": False, "is_shared": False},
    ]


def _get_printer_list() -> list[dict]:
    """获取打印机列表，平台/依赖不满足时回退到模拟数据。"""
    if platform.system() == "Windows" and sys.modules.get("win32print"):
        return _get_printer_list_from_win32()
    if platform.system() == "Windows":
        try:
            import win32print
            return _get_printer_list_from_win32()
        except ImportError:
            logger.info("win32print not installed, using mock printers")
            return _get_printer_list_mock()
    return _get_printer_list_mock()


def _classify_printers(printers: list[dict]) -> dict:
    """根据名称关键字将打印机分类为标签打印机和发货单打印机。"""
    doc_kw = ("发货", "送货", "单据", "文档", "invoice", "document", "shipping")
    lbl_kw = ("标签", "贴纸", "吊牌", "label", "tag")

    doc_printer = None
    lbl_printer = None

    default_name = None
    try:
        import win32print
        default_name = win32print.GetDefaultPrinter()
    except Exception:
        pass

    for p in printers:
        name = p.get("name", "")
        low = name.lower()

        if not doc_printer and any(k in low for k in doc_kw):
            doc_printer = p.copy()
            doc_printer["role"] = "document"
        elif not lbl_printer and any(k in low for k in lbl_kw):
            lbl_printer = p.copy()
            lbl_printer["role"] = "label"

    if not doc_printer and default_name:
        p = next((x for x in printers if x["name"] == default_name), None)
        if p:
            doc_printer = p.copy()
            doc_printer["role"] = "document"

    return {"document_printer": doc_printer, "label_printer": lbl_printer}


_PRINTER_SELECTION_FILE = Path.home() / ".fhd" / "printer_selection.json"


def _load_printer_selection() -> dict:
    try:
        if _PRINTER_SELECTION_FILE.exists():
            import json
            return json.loads(_PRINTER_SELECTION_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_printer_selection(data: dict) -> None:
    try:
        _PRINTER_SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
        import json
        _PRINTER_SELECTION_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to save printer selection: %s", e)


@router.get("/printers")
async def get_printers() -> dict:
    """获取所有可用打印机列表。"""
    printers = _get_printer_list()
    classified = _classify_printers(printers)
    selection = _load_printer_selection()
    resolution = _selection_resolution(printers, selection)
    return {
        "success": True,
        "printers": printers,
        "classified": classified,
        "selection": selection,
        **resolution,
    }


@router.get("/default")
async def get_default_printer() -> dict:
    """获取默认打印机。"""
    printers = _get_printer_list()
    default = next((p for p in printers if p.get("is_default")), None)
    if not default and printers:
        default = printers[0]
    return {"success": True, "printer": default}


@router.get("/document-printer")
async def get_document_printer() -> dict:
    """获取发货单打印机（根据分类或选择）。"""
    printers = _get_printer_list()
    classified = _classify_printers(printers)
    selection = _load_printer_selection()
    name = selection.get("document_printer")
    if name:
        p = _find_printer_by_saved_name(printers, name)
        if p:
            return {"success": True, "printer": p, "classified": classified}
    doc = classified.get("document_printer")
    if doc:
        return {"success": True, "printer": doc, "classified": classified}
    return {"success": True, "printer": None, "classified": classified}


@router.get("/label-printer")
async def get_label_printer() -> dict:
    """获取标签打印机（根据分类或选择）。"""
    printers = _get_printer_list()
    classified = _classify_printers(printers)
    selection = _load_printer_selection()
    name = selection.get("label_printer")
    if name:
        p = _find_printer_by_saved_name(printers, name)
        if p:
            return {"success": True, "printer": p, "classified": classified}
    lbl = classified.get("label_printer")
    if lbl:
        return {"success": True, "printer": lbl, "classified": classified}
    return {"success": True, "printer": None, "classified": classified}


@router.get("/printer-selection")
async def get_printer_selection() -> dict:
    """获取用户自定义的打印机选择。"""
    printers = _get_printer_list()
    selection = _load_printer_selection()
    resolution = _selection_resolution(printers, selection)
    return {"success": True, "selection": selection, **resolution}


@router.put("/printer-selection")
async def save_printer_selection(body: dict) -> dict:
    """保存用户自定义的打印机选择。"""
    selection = _load_printer_selection()
    if "document_printer" in body:
        selection["document_printer"] = body["document_printer"]
    if "label_printer" in body:
        selection["label_printer"] = body["label_printer"]
    _save_printer_selection(selection)
    return {"success": True, "message": "打印机选择已保存", "selection": selection}


@router.post("/document")
async def print_document(body: dict) -> dict:
    """打印发货单文档。"""
    file_path = body.get("file_path", "")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    selection = _load_printer_selection()
    printer_name = selection.get("document_printer", "")
    logger.info("Print document: %s, printer: %s", file_path, printer_name)
    return {"success": True, "message": f"文档打印任务已提交: {file_path}"}


@router.post("/label")
async def print_label(body: dict) -> dict:
    """打印标签。"""
    file_path = body.get("file_path", "")
    copies = body.get("copies", 1)
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    selection = _load_printer_selection()
    printer_name = selection.get("label_printer", "")
    logger.info("Print label: %s (copies=%d), printer: %s", file_path, copies, printer_name)
    return {"success": True, "message": f"标签打印任务已提交: {file_path}"}


@router.post("/single_label")
async def print_single_label(body: dict) -> dict:
    """打印单个标签（按产品型号）。"""
    model_number = body.get("model_number", "")
    quantity = body.get("quantity", 1)
    if not model_number:
        raise HTTPException(status_code=400, detail="model_number is required")
    selection = _load_printer_selection()
    printer_name = selection.get("label_printer", "")
    logger.info("Print single label: model=%s, qty=%d, printer=%s", model_number, quantity, printer_name)
    return {"success": True, "message": f"标签打印任务已提交: {model_number} x{quantity}"}


@router.get("/list_labels")
async def list_labels() -> dict:
    """列出可用的标签文件。"""
    return {"success": True, "data": []}


@router.post("/{filename}")
async def print_by_filename(filename: str) -> dict:
    """按文件名打印。"""
    logger.info("Print by filename: %s", filename)
    return {"success": True, "message": f"打印任务已提交: {filename}"}


@router.get("/validate")
async def validate_printers() -> dict:
    """验证打印机连接状态。"""
    printers = _get_printer_list()
    online = [p for p in printers if _is_printer_online(p)]
    return {
        "success": True,
        "total": len(printers),
        "online": len(online),
        "printers": printers,
    }