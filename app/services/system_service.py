"""
系统设置服务模块

提供系统配置、开机自启等业务逻辑。
"""

import os
import sys
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SystemService:
    """系统服务类"""
    
    def __init__(self):
        """初始化系统服务"""
        self.app_name = "XCAGI"
        self.app_path = os.path.abspath(os.path.dirname(__file__))
    
    def get_startup_config(self) -> Dict[str, Any]:
        """
        获取开机自启配置
        
        Returns:
            结果字典：
                - enabled: 是否已启用开机自启
                - app_path: 应用路径
                - app_name: 应用名称
        """
        try:
            if sys.platform == "win32":
                import winreg
                
                try:
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
                    
                    try:
                        value, _ = winreg.QueryValueEx(key, self.app_name)
                        enabled = True
                        startup_path = value
                    except FileNotFoundError:
                        enabled = False
                        startup_path = None
                    finally:
                        winreg.CloseKey(key)
                    
                    return {
                        "enabled": enabled,
                        "app_path": self.app_path,
                        "startup_path": startup_path,
                        "platform": "windows"
                    }
                    
                except Exception as e:
                    logger.error(f"获取开机自启配置失败：{e}")
                    return {
                        "enabled": False,
                        "app_path": self.app_path,
                        "error": str(e),
                        "platform": "windows"
                    }
            else:
                return {
                    "enabled": False,
                    "app_path": self.app_path,
                    "platform": sys.platform,
                    "message": "当前平台不支持开机自启"
                }
                
        except Exception as e:
            logger.exception(f"获取开机自启配置失败：{e}")
            return {
                "enabled": False,
                "app_path": self.app_path,
                "error": str(e)
            }
    
    def enable_startup(self) -> Dict[str, Any]:
        """
        启用开机自启
        
        Returns:
            结果字典
        """
        try:
            if sys.platform == "win32":
                import winreg
                
                app_exe = sys.executable
                script_path = os.path.join(self.app_path, "..", "..", "run.py")
                script_path = os.path.abspath(script_path)
                
                startup_command = f'"{app_exe}" "{script_path}"'
                
                try:
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                    winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, startup_command)
                    winreg.CloseKey(key)
                    
                    logger.info(f"开机自启已启用：{startup_command}")
                    
                    return {
                        "success": True,
                        "message": "开机自启已启用",
                        "command": startup_command
                    }
                    
                except Exception as e:
                    logger.error(f"启用开机自启失败：{e}")
                    return {
                        "success": False,
                        "message": f"启用失败：{str(e)}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"当前平台不支持开机自启：{sys.platform}"
                }
                
        except Exception as e:
            logger.exception(f"启用开机自启失败：{e}")
            return {
                "success": False,
                "message": f"启用失败：{str(e)}"
            }
    
    def disable_startup(self) -> Dict[str, Any]:
        """
        禁用开机自启
        
        Returns:
            结果字典
        """
        try:
            if sys.platform == "win32":
                import winreg
                
                try:
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
                    winreg.DeleteValue(key, self.app_name)
                    winreg.CloseKey(key)
                    
                    logger.info("开机自启已禁用")
                    
                    return {
                        "success": True,
                        "message": "开机自启已禁用"
                    }
                    
                except FileNotFoundError:
                    return {
                        "success": True,
                        "message": "开机自启原本就未启用"
                    }
                except Exception as e:
                    logger.error(f"禁用开机自启失败：{e}")
                    return {
                        "success": False,
                        "message": f"禁用失败：{str(e)}"
                    }
            else:
                return {
                    "success": False,
                    "message": f"当前平台不支持开机自启：{sys.platform}"
                }
                
        except Exception as e:
            logger.exception(f"禁用开机自启失败：{e}")
            return {
                "success": False,
                "message": f"禁用失败：{str(e)}"
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            结果字典：
                - platform: 操作系统平台
                - python_version: Python 版本
                - app_path: 应用路径
                - working_directory: 工作目录
        """
        try:
            import platform
            
            return {
                "platform": sys.platform,
                "platform_version": platform.version(),
                "python_version": sys.version,
                "app_path": self.app_path,
                "working_directory": os.getcwd(),
                "executable": sys.executable
            }
            
        except Exception as e:
            logger.exception(f"获取系统信息失败：{e}")
            return {
                "error": str(e)
            }
    
    def get_printer_config(self) -> Dict[str, Any]:
        """
        获取打印机配置
        
        Returns:
            结果字典
        """
        try:
            from app.services.printer_service import PrinterService
            
            printer_service = PrinterService()
            
            try:
                printers = printer_service.list_printers()
                default_printer = printer_service.get_default_printer()
                
                return {
                    "success": True,
                    "printers": printers,
                    "default_printer": default_printer
                }
                
            except Exception as e:
                logger.error(f"获取打印机配置失败：{e}")
                return {
                    "success": False,
                    "message": f"获取打印机配置失败：{str(e)}",
                    "printers": [],
                    "default_printer": None
                }
                
        except Exception as e:
            logger.exception(f"获取打印机配置失败：{e}")
            return {
                "success": False,
                "message": f"获取打印机配置失败：{str(e)}"
            }
    
    def set_default_printer(self, printer_name: str) -> Dict[str, Any]:
        """
        设置默认打印机
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            结果字典
        """
        try:
            from app.services.printer_service import PrinterService
            
            printer_service = PrinterService()
            
            try:
                success = printer_service.set_default_printer(printer_name)
                
                if success:
                    return {
                        "success": True,
                        "message": f"已设置默认打印机：{printer_name}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"设置默认打印机失败：{printer_name}"
                    }
                    
            except Exception as e:
                logger.error(f"设置默认打印机失败：{e}")
                return {
                    "success": False,
                    "message": f"设置失败：{str(e)}"
                }
                
        except Exception as e:
            logger.exception(f"设置默认打印机失败：{e}")
            return {
                "success": False,
                "message": f"设置失败：{str(e)}"
            }


def get_system_service() -> SystemService:
    """获取系统服务实例"""
    return SystemService()
