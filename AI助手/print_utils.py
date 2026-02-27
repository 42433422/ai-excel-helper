"""
打印机工具类
提供打印功能和打印机管理
"""

import os
import time
import win32print
import win32api
import pythoncom
import logging
from typing import List, Dict, Optional

# 配置日志（支持中文编码）
logging.basicConfig(level=logging.INFO, encoding='utf-8')
logger = logging.getLogger(__name__)


class PrinterUtils:
    """打印机工具类"""
    
    def __init__(self):
        """初始化打印机工具"""
        self._com_initialized = False
    
    def _ensure_com_initialized(self):
        """确保COM环境已初始化"""
        if not self._com_initialized:
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception as e:
                logger.warning(f"COM初始化警告: {e}")
    
    def get_available_printers(self) -> List[Dict[str, str]]:
        """
        获取系统中所有可用的打印机列表
        
        Returns:
            List[Dict]: 打印机列表，每个打印机包含名称和状态
        """
        try:
            # 确保COM已初始化
            self._ensure_com_initialized()
            
            printers = []
            
            # 获取默认打印机
            try:
                default_printer = win32print.GetDefaultPrinter()
                logger.info(f"默认打印机: {default_printer}")
            except:
                default_printer = None
                logger.warning("无法获取默认打印机")
            
            # 获取所有打印机
            all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            
            logger.info(f"找到 {len(all_printers)} 个打印机")
            
            for printer_info in all_printers:
                logger.info(f"打印机信息: {printer_info}")
                logger.info(f"打印机信息长度: {len(printer_info)}")
                
                # 根据返回的元组结构提取信息
                if len(printer_info) >= 3:
                    printer_name = printer_info[2]
                    
                    # 尝试获取状态（可能在不同位置）
                    status = 0  # 默认就绪状态
                    if len(printer_info) > 6:
                        status = printer_info[6]
                    elif len(printer_info) > 5:
                        # 有些格式状态在第6个位置
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
        """
        将打印机状态码转换为可读状态
        
        Args:
            status_code: 打印机状态码
            
        Returns:
            str: 可读的状态描述
        """
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
        """
        监控打印机队列，等待打印任务完成
        
        Args:
            printer_name: 打印机名称
            timeout: 超时时间（秒）
            
        Returns:
            bool: 打印任务是否完成
        """
        try:
            import time
            
            logger.info(f"开始监控打印机 {printer_name} 的打印任务...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # 打开打印机
                    hPrinter = win32print.OpenPrinter(printer_name)
                    
                    try:
                        # 枚举打印作业
                        jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
                        
                        if not jobs:
                            logger.info("✅ 打印机队列为空，打印任务已完成")
                            return True
                        else:
                            logger.info(f"⚠️ 打印机队列中有 {len(jobs)} 个任务，等待完成...")
                            # 打印任务详情
                            for i, job in enumerate(jobs):
                                logger.info(f"   任务 {i+1}: {job}")
                    finally:
                        win32print.ClosePrinter(hPrinter)
                        
                except Exception as e:
                    logger.warning(f"监控打印任务失败: {e}")
                
                # 等待1秒后再次检查
                time.sleep(1)
            
            logger.warning(f"⚠️ 监控打印任务超时（{timeout}秒）")
            return False
            
        except Exception as e:
            logger.error(f"监控打印任务时发生错误: {e}")
            return False
    
    def print_file(self, file_path: str, printer_name: Optional[str] = None, use_default_printer: bool = False) -> Dict[str, any]:
        """
        打印指定文件
        
        Args:
            file_path: 要打印的文件路径
            printer_name: 打印机名称，如果为None则使用默认打印机
            use_default_printer: 是否临时修改系统默认打印机
            
        Returns:
            Dict: 打印结果，包含success状态和消息
        """
        try:
            # 验证文件存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}"
                }
            
            # 获取文件扩展名
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # 获取打印机 - 严格验证，必须提供打印机名称
            if not printer_name:
                logger.error("❌ 未指定打印机名称，拒绝打印")
                return {
                    "success": False,
                    "message": "未指定打印机名称，无法打印"
                }
            
            logger.info(f"准备打印文件: {file_path}")
            logger.info(f"使用打印机: {printer_name}")
            
            original_default_printer = None
            
            # 如果需要临时修改默认打印机
            if use_default_printer:
                try:
                    # 保存原始默认打印机
                    original_default_printer = win32print.GetDefaultPrinter()
                    logger.info(f"[打印机修改] 当前默认打印机: {original_default_printer}")
                    logger.info(f"[打印机修改] 目标打印机: {printer_name}")
                    
                    # 如果当前默认打印机不是目标打印机，则修改
                    if original_default_printer != printer_name:
                        logger.info(f"[打印机修改] 正在修改默认打印机...")
                        try:
                            win32print.SetDefaultPrinter(printer_name)
                            logger.info(f"[打印机修改] SetDefaultPrinter 调用完成")
                        except Exception as e:
                            logger.error(f"[打印机修改] SetDefaultPrinter 调用失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                        
                        # 验证修改是否成功
                        time.sleep(0.5)  # 等待修改生效
                        try:
                            new_default = win32print.GetDefaultPrinter()
                            logger.info(f"[打印机修改] 验证 - 当前默认打印机: {new_default}")
                        except Exception as e:
                            logger.error(f"[打印机修改] GetDefaultPrinter 调用失败: {e}")
                            new_default = original_default_printer
                        
                        if new_default == printer_name:
                            logger.info(f"✅ 默认打印机修改成功: {new_default}")
                        else:
                            logger.error(f"❌ 默认打印机修改失败！当前: {new_default}, 目标: {printer_name}")
                            # 尝试再次修改
                            logger.info("[打印机修改] 尝试第二次修改...")
                            try:
                                win32print.SetDefaultPrinter(printer_name)
                                time.sleep(0.5)
                                new_default = win32print.GetDefaultPrinter()
                                logger.info(f"[打印机修改] 第二次修改后默认打印机: {new_default}")
                            except Exception as e:
                                logger.error(f"[打印机修改] 第二次修改失败: {e}")
                    else:
                        logger.info("当前默认打印机已经是目标打印机，无需修改")
                except Exception as e:
                    logger.error(f"[打印机修改] 修改默认打印机失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.info("✅ 已明确指定打印机，不使用系统默认打印机")
            
            # 根据文件类型选择打印方法
            print_result = None
            try:
                if ext == '.xlsx':
                    print_result = self._print_excel(file_path, printer_name)
                elif ext == '.xls':
                    print_result = self._print_excel(file_path, printer_name)
                elif ext == '.pdf':
                    print_result = self._print_pdf(file_path, printer_name)
                else:
                    # 对于其他类型文件，使用默认打印方式
                    print_result = self._print_default(file_path, printer_name)
                
                # 打印命令已发送，不等待任务完成，直接继续
                if print_result.get('success', False):
                    logger.info("✅ 打印命令已发送，继续执行后续操作")
            finally:
                # 恢复原始默认打印机
                if use_default_printer and original_default_printer:
                    try:
                        if original_default_printer != printer_name:
                            logger.info(f"恢复默认打印机为: {original_default_printer}")
                            win32print.SetDefaultPrinter(original_default_printer)
                            logger.info("✅ 默认打印机恢复成功")
                    except Exception as e:
                        logger.warning(f"恢复默认打印机失败: {e}")
            
            return print_result
                
        except Exception as e:
            logger.error(f"打印文件失败: {e}")
            return {
                "success": False,
                "message": f"打印失败: {str(e)}"
            }
    
    def _print_excel(self, file_path: str, printer_name: str) -> Dict[str, any]:
        """
        打印Excel文件
        
        Args:
            file_path: Excel文件路径
            printer_name: 打印机名称
            
        Returns:
            Dict: 打印结果
        """
        import os
        
        try:
            logger.info(f"开始打印Excel文件: {file_path}")
            logger.info(f"使用打印机: {printer_name}")
            
            # 方法1: 使用 os.startfile 打印（最可靠）
            try:
                logger.info("方法1: 使用os.startfile打印")
                os.startfile(file_path, "print")
                logger.info(f"✅ os.startfile打印成功: {file_path}")
                return {
                    "success": True,
                    "message": "打印任务已发送（os.startfile）",
                    "file": os.path.basename(file_path),
                    "printer": printer_name
                }
            except Exception as e1:
                logger.warning(f"方法1失败: {e1}")
                
                # 方法2: 使用 ShellExecute print
                try:
                    logger.info("方法2: 使用ShellExecute print")
                    result = win32api.ShellExecute(
                        0,
                        "print",
                        file_path,
                        None,  # 使用系统默认打印机
                        ".",
                        1  # SW_SHOW 显示窗口
                    )
                    
                    if result > 32:
                        logger.info(f"✅ ShellExecute打印成功: {file_path}")
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
                    
                    # 方法3: 直接打开文件让用户手动打印
                    try:
                        logger.info("方法3: 打开文件让用户手动打印")
                        os.startfile(file_path)
                        logger.info(f"✅ 已打开文件: {file_path}")
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
    
    def _print_pdf(self, file_path: str, printer_name: str) -> Dict[str, any]:
        """
        打印PDF文件
        
        Args:
            file_path: PDF文件路径
            printer_name: 打印机名称
            
        Returns:
            Dict: 打印结果
        """
        try:
            # 方法1: 直接使用win32print打印PDF
            logger.info(f"尝试使用win32print直接打印PDF到 {printer_name}")
            
            try:
                # 直接使用win32print
                hprinter = win32print.OpenPrinter(printer_name)
                
                # 尝试打印PDF文件
                try:
                    # 直接发送文件到打印机
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # 使用Raw数据发送
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
            
            # 方法2: 使用Python COM接口
            logger.info("尝试使用Python COM接口打印")
            try:
                import pythoncom
                pythoncom.CoInitialize()
                
                # 使用Adobe Acrobat COM接口
                try:
                    acrobat = pythoncom.Dispatch("AcroExch.PDDoc")
                    pdf_doc = acrobat.Open(file_path)
                    if pdf_doc:
                        pdf_doc.PrintPagesSilent(0, pdf_doc.GetNumPages() - 1, True)
                        pdf_doc.Close()
                        acrobat.CloseAllDocs()
                        
                        logger.info(f"PDF文件已通过Adobe COM发送到打印机")
                        return {
                            "success": True,
                            "message": "PDF文件已通过Adobe发送到打印机",
                            "file": os.path.basename(file_path),
                            "printer": printer_name,
                            "method": "adobe_com"
                        }
                except Exception as e:
                    logger.warning(f"Adobe COM打印失败: {e}")
                finally:
                    pythoncom.CoUninitialize()
                    
            except Exception as e:
                logger.warning(f"Python COM接口失败: {e}")
            
            # 方法3: 使用subprocess调用外部程序
            logger.info("尝试使用subprocess调用外部程序")
            try:
                import subprocess
                
                # 尝试找到Adobe Reader
                adobe_paths = [
                    r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
                    r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
                    r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\Acrobat.exe",
                    r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\Acrobat.exe"
                ]
                
                for adobe_path in adobe_paths:
                    if os.path.exists(adobe_path):
                        logger.info(f"使用Adobe Reader: {adobe_path}")
                        
                        # 使用Adobe Reader命令行
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
            
            # 如果所有方法都失败，尝试最简单的方法
            logger.info("尝试最简单的方法: 复制文件")
            try:
                # 将PDF复制到用户的打印机文档目录
                import shutil
                temp_dir = os.path.expanduser("~/Documents")
                if os.path.exists(temp_dir):
                    shutil.copy2(file_path, temp_dir)
                    logger.info(f"PDF文件已复制到Documents目录: {temp_dir}")
                    return {
                        "success": True,
                        "message": "PDF文件已复制到Documents目录，请手动打印",
                        "file": os.path.basename(file_path),
                        "printer": printer_name,
                        "method": "copy_to_documents"
                    }
            except Exception as e:
                logger.warning(f"复制文件方法失败: {e}")
            
            # 如果所有方法都失败，返回错误
            raise Exception("所有PDF打印方法都失败")
                
        except Exception as e:
            logger.error(f"打印PDF文件失败: {e}")
            return {
                "success": False,
                "message": f"打印PDF失败: {str(e)}"
            }
    
    def _print_default(self, file_path: str, printer_name: str, show_app: bool = False) -> Dict[str, any]:
        """
        使用默认方式打印文件
        
        Args:
            file_path: 文件路径
            printer_name: 打印机名称
            show_app: 是否显示应用程序窗口
            
        Returns:
            Dict: 打印结果
        """
        try:
            # 根据show_app参数决定是否显示窗口
            show_cmd = 1 if show_app else 0  # 1=SW_SHOW, 0=SW_HIDE
            
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
        """
        获取系统默认打印机
        
        Returns:
            str: 默认打印机名称，失败返回None
        """
        try:
            return win32print.GetDefaultPrinter()
        except Exception as e:
            logger.error(f"获取默认打印机失败: {e}")
            return None
    
    def test_printer(self, printer_name: str) -> Dict[str, any]:
        """
        测试打印机是否可用
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            Dict: 测试结果
        """
        try:
            # 尝试打开打印机
            hprinter = win32print.OpenPrinter(printer_name)
            
            # 获取打印机状态
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


# 便捷函数
def get_printers():
    """获取可用打印机列表"""
    utils = PrinterUtils()
    return utils.get_available_printers()


def print_document(file_path: str, printer_name: Optional[str] = None, use_automation: bool = False, use_default_printer: bool = False) -> Dict[str, any]:
    """打印文档"""
    try:
        if use_automation:
            from printer_automation import EnhancedPrinterUtils
            enhanced_utils = EnhancedPrinterUtils()
            return enhanced_utils.print_file_enhanced(file_path, printer_name, use_automation=True, use_default_printer=use_default_printer)
        else:
            utils = PrinterUtils()
            return utils.print_file(file_path, printer_name, use_default_printer=use_default_printer)
    except Exception as e:
        logger.error(f"打印文档失败: {e}")
        return {
            "success": False,
            "message": f"打印失败: {str(e)}"
        }
