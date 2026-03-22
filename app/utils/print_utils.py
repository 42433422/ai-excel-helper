import logging
import os
import time
from typing import Dict, List, Optional

import pythoncom
import win32api
import win32print

logging.basicConfig(level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)


class PrinterUtils:
    def __init__(self):
        self._com_initialized = False

    def _ensure_com_initialized(self):
        if not self._com_initialized:
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception as e:
                logger.warning(f"COM初始化警告: {e}")

    def get_available_printers(self) -> List[Dict[str, str]]:
        try:
            self._ensure_com_initialized()
            printers = []

            try:
                default_printer = win32print.GetDefaultPrinter()
                logger.info(f"默认打印机: {default_printer}")
            except:
                default_printer = None
                logger.warning("无法获取默认打印机")

            all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

            logger.info(f"找到 {len(all_printers)} 个打印机")

            for printer_info in all_printers:
                logger.info(f"打印机信息: {printer_info}")
                logger.info(f"打印机信息长度: {len(printer_info)}")

                if len(printer_info) >= 3:
                    printer_name = printer_info[2]

                    status = 0
                    if len(printer_info) > 6:
                        status = printer_info[6]
                    elif len(printer_info) > 5:
                        try:
                            status = int(printer_info[5]) if printer_info[5] else 0
                        except:
                            pass

                    status_text = self._get_printer_status(status)

                is_default = (printer_name == default_printer)

                printers.append({
                    "name": printer_name,
                    "status": status_text,
                    "is_default": is_default
                })

                logger.info(f"  - {printer_name} (默认: {is_default}, 状态: {status_text})")

            return printers

        except Exception as e:
            logger.error(f"获取打印机列表失败: {e}", exc_info=True)
            return []

    def _get_printer_status(self, status_code: int) -> str:
        status_map = {
            win32print.PRINTER_STATUS_PAUSED: "已暂停",
            win32print.PRINTER_STATUS_ERROR: "错误",
            win32print.PRINTER_STATUS_PENDING_DELETION: "正在删除",
            win32print.PRINTER_STATUS_PAPER_JAM: "卡纸",
            win32print.PRINTER_STATUS_PAPER_OUT: "缺纸",
            win32print.PRINTER_STATUS_MANUAL_FEED: "等待手动送纸",
            win32print.PRINTER_STATUS_PRINTING: "打印中",
            win32print.PRINTER_STATUS_OUTPUT_BIN_FULL: "输出纸盒已满",
            win32print.PRINTER_STATUS_NOT_AVAILABLE: "不可用",
            win32print.PRINTER_STATUS_WAITING: "等待中",
            win32print.PRINTER_STATUS_PROCESSING: "处理中",
            win32print.PRINTER_STATUS_INITIALIZING: "初始化中",
            win32print.PRINTER_STATUS_WARMING_UP: "预热中",
            win32print.PRINTER_STATUS_TONER_LOW: "墨粉不足",
            win32print.PRINTER_STATUS_NO_TONER: "无墨粉",
            win32print.PRINTER_STATUS_PAGE_PUNT: "页面跳过",
            win32print.PRINTER_STATUS_USER_INTERVENTION: "需要用户干预",
            win32print.PRINTER_STATUS_OUT_OF_MEMORY: "内存不足",
            win32print.PRINTER_STATUS_DOOR_OPEN: "前门打开",
            win32print.PRINTER_STATUS_SERVER_UNKNOWN: "服务器未知",
            win32print.PRINTER_STATUS_POWER_SAVE: "节能模式",
        }

        return status_map.get(status_code, "就绪")

    def monitor_print_job(self, printer_name: str, timeout: int = 60) -> bool:
        try:
            logger.info(f"开始监控打印机 {printer_name} 的打印任务...")

            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    hPrinter = win32print.OpenPrinter(printer_name)

                    try:
                        jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)

                        if not jobs:
                            logger.info("打印机队列为空，打印任务已完成")
                            return True
                        else:
                            logger.info(f"打印机队列中有 {len(jobs)} 个任务，等待完成...")
                            for i, job in enumerate(jobs):
                                logger.info(f"   任务 {i+1}: {job}")
                    finally:
                        win32print.ClosePrinter(hPrinter)

                except Exception as e:
                    logger.warning(f"监控打印任务失败: {e}")

                time.sleep(1)

            logger.warning(f"监控打印任务超时（{timeout}秒）")
            return False

        except Exception as e:
            logger.error(f"监控打印任务时发生错误: {e}")
            return False

    def print_file(self, file_path: str, printer_name: Optional[str] = None, use_default_printer: bool = False) -> Dict:
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}"
                }

            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            if not printer_name:
                logger.error("未指定打印机名称，拒绝打印")
                return {
                    "success": False,
                    "message": "未指定打印机名称，无法打印"
                }

            logger.info(f"准备打印文件: {file_path}")
            logger.info(f"使用打印机: {printer_name}")

            original_default_printer = None

            if use_default_printer:
                try:
                    original_default_printer = win32print.GetDefaultPrinter()
                    logger.info(f"当前默认打印机: {original_default_printer}")
                    logger.info(f"目标打印机: {printer_name}")

                    if original_default_printer != printer_name:
                        logger.info(f"正在修改默认打印机...")
                        try:
                            win32print.SetDefaultPrinter(printer_name)
                            logger.info(f"SetDefaultPrinter 调用完成")
                        except Exception as e:
                            logger.error(f"SetDefaultPrinter 调用失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())

                        time.sleep(0.5)
                        try:
                            new_default = win32print.GetDefaultPrinter()
                            logger.info(f"验证 - 当前默认打印机: {new_default}")
                        except Exception as e:
                            logger.error(f"GetDefaultPrinter 调用失败: {e}")
                            new_default = original_default_printer

                        if new_default == printer_name:
                            logger.info(f"默认打印机修改成功: {new_default}")
                        else:
                            logger.error(f"默认打印机修改失败！当前: {new_default}, 目标: {printer_name}")
                            try:
                                win32print.SetDefaultPrinter(printer_name)
                                time.sleep(0.5)
                                new_default = win32print.GetDefaultPrinter()
                                logger.info(f"第二次修改后默认打印机: {new_default}")
                            except Exception as e:
                                logger.error(f"第二次修改失败: {e}")
                    else:
                        logger.info("当前默认打印机已经是目标打印机，无需修改")
                except Exception as e:
                    logger.error(f"修改默认打印机失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.info("已明确指定打印机，不使用系统默认打印机")

            print_result = None
            try:
                if ext in ['.xlsx', '.xls']:
                    print_result = self._print_excel(file_path, printer_name)
                elif ext == '.pdf':
                    print_result = self._print_pdf(file_path, printer_name)
                else:
                    print_result = self._print_default(file_path, printer_name)

                if print_result.get('success', False):
                    logger.info("打印命令已发送，继续执行后续操作")
            finally:
                if use_default_printer and original_default_printer:
                    try:
                        if original_default_printer != printer_name:
                            logger.info(f"恢复默认打印机为: {original_default_printer}")
                            win32print.SetDefaultPrinter(original_default_printer)
                            logger.info("默认打印机恢复成功")
                    except Exception as e:
                        logger.warning(f"恢复默认打印机失败: {e}")

            return print_result

        except Exception as e:
            logger.error(f"打印文件失败: {e}")
            return {
                "success": False,
                "message": f"打印失败: {str(e)}"
            }

    def _print_excel(self, file_path: str, printer_name: str) -> Dict:
        try:
            logger.info(f"开始打印Excel文件: {file_path}")
            logger.info(f"使用打印机: {printer_name}")

            try:
                logger.info("方法1: 使用os.startfile打印")
                os.startfile(file_path, "print")
                logger.info(f"os.startfile打印成功: {file_path}")
                return {
                    "success": True,
                    "message": "打印任务已发送（os.startfile）",
                    "file": os.path.basename(file_path),
                    "printer": printer_name
                }
            except Exception as e1:
                logger.warning(f"方法1失败: {e1}")

                try:
                    logger.info("方法2: 使用ShellExecute print")
                    result = win32api.ShellExecute(
                        0,
                        "print",
                        file_path,
                        None,
                        ".",
                        1
                    )

                    if result > 32:
                        logger.info(f"ShellExecute打印成功: {file_path}")
                        return {
                            "success": True,
                            "message": "打印任务已发送到打印机",
                            "file": os.path.basename(file_path),
                            "printer": printer_name
                        }
                    else:
                        raise Exception(f"ShellExecute失败，错误代码: {result}")

                except Exception as e2:
                    logger.warning(f"方法2失败: {e2}")

                    try:
                        logger.info("方法3: 打开文件让用户手动打印")
                        os.startfile(file_path)
                        logger.info(f"已打开文件: {file_path}")
                        return {
                            "success": True,
                            "message": "文件已打开，请手动打印",
                            "file": os.path.basename(file_path),
                            "printer": printer_name,
                            "manual": True
                        }
                    except Exception as e3:
                        logger.error(f"方法3也失败: {e3}")
                        raise Exception(f"所有打印方法都失败: {e1}; {e2}; {e3}")

        except Exception as e:
            logger.error(f"打印Excel文件失败: {e}")
            return {
                "success": False,
                "message": f"打印失败: {str(e)}"
            }

    def _print_pdf(self, file_path: str, printer_name: str) -> Dict:
        try:
            logger.info(f"尝试使用win32print直接打印PDF到 {printer_name}")

            try:
                hprinter = win32print.OpenPrinter(printer_name)

                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()

                    job_id = win32print.StartDocPrinter(hprinter, 1, ("PDF Job", None, "RAW"))
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, file_data)
                    win32print.EndPagePrinter(hprinter)
                    win32print.EndDocPrinter(hprinter)

                    logger.info(f"PDF文件已通过win32print发送到打印机: {file_path}")
                    return {
                        "success": True,
                        "message": "PDF文件已发送到打印机",
                        "file": os.path.basename(file_path),
                        "printer": printer_name,
                        "method": "win32print"
                    }
                finally:
                    win32print.ClosePrinter(hprinter)

            except Exception as e:
                logger.warning(f"win32print打印失败: {e}")

            logger.info("尝试使用subprocess调用外部程序")
            try:
                import subprocess

                adobe_paths = [
                    r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
                    r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
                ]

                for adobe_path in adobe_paths:
                    if os.path.exists(adobe_path):
                        logger.info(f"使用Adobe Reader: {adobe_path}")

                        result = subprocess.run([
                            adobe_path,
                            "/t",
                            file_path,
                            printer_name
                        ], check=True, timeout=30, capture_output=True)

                        logger.info(f"PDF文件已通过Adobe Reader发送到打印机")
                        return {
                            "success": True,
                            "message": "PDF文件已通过Adobe Reader发送到打印机",
                            "file": os.path.basename(file_path),
                            "printer": printer_name,
                            "method": "adobe_cli"
                        }

                logger.warning("未找到Adobe Reader")

            except Exception as e:
                logger.warning(f"subprocess方法失败: {e}")

            raise Exception("所有PDF打印方法都失败")

        except Exception as e:
            logger.error(f"打印PDF文件失败: {e}")
            return {
                "success": False,
                "message": f"打印PDF失败: {str(e)}"
            }

    def _print_default(self, file_path: str, printer_name: str, show_app: bool = False) -> Dict:
        try:
            show_cmd = 1 if show_app else 0

            win32api.ShellExecute(
                0,
                "print",
                file_path,
                f'/d:"{printer_name}"',
                ".",
                show_cmd
            )

            app_status = "（显示应用窗口）" if show_app else "（隐藏应用窗口）"
            logger.info(f"文件已发送到打印机{app_status}: {file_path}")
            return {
                "success": True,
                "message": f"打印任务已发送到打印机{app_status}",
                "file": os.path.basename(file_path),
                "printer": printer_name,
                "show_app": show_app
            }

        except Exception as e:
            logger.error(f"打印文件失败: {e}")
            return {
                "success": False,
                "message": f"打印失败: {str(e)}"
            }

    def get_default_printer(self) -> Optional[str]:
        try:
            return win32print.GetDefaultPrinter()
        except Exception as e:
            logger.error(f"获取默认打印机失败: {e}")
            return None

    def test_printer(self, printer_name: str) -> Dict:
        try:
            hprinter = win32print.OpenPrinter(printer_name)

            printer_info = win32print.GetPrinter(hprinter, 2)
            status = printer_info['Status']
            status_text = self._get_printer_status(status)

            win32print.ClosePrinter(hprinter)

            return {
                "success": True,
                "available": True,
                "printer": printer_name,
                "status": status_text
            }

        except Exception as e:
            logger.error(f"测试打印机失败: {e}")
            return {
                "success": False,
                "available": False,
                "printer": printer_name,
                "message": str(e)
            }

    def get_document_printer(self) -> Optional[str]:
        """获取发货单打印机"""
        try:
            printers = self.get_available_printers()
            if not printers:
                return None

            keywords = ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式', 'hp', 'canon', 'epson']

            for printer in printers:
                name_lower = printer['name'].lower()
                if any(kw in name_lower for kw in keywords):
                    return printer['name']

            return printers[0]['name'] if printers else None

        except Exception as e:
            logger.error(f"获取发货单打印机失败: {e}")
            return None

    def get_label_printer(self) -> Optional[str]:
        """获取标签打印机"""
        try:
            printers = self.get_available_printers()
            if not printers:
                return None

            keywords = ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', 'zebra']

            for printer in printers:
                name_lower = printer['name'].lower()
                if any(kw in name_lower for kw in keywords):
                    return printer['name']

            return printers[-1]['name'] if printers else None

        except Exception as e:
            logger.error(f"获取标签打印机失败: {e}")
            return None
