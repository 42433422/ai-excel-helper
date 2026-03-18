"""
路径工具函数模块

提供应用目录、数据目录等路径相关工具函数。
"""

import os
import sys


def get_base_dir() -> str:
    """
    获取应用基础目录（兼容 PyInstaller 打包）
    
    Returns:
        应用基础目录路径
    """
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_app_data_dir() -> str:
    """
    获取应用程序数据目录
    
    Returns:
        应用程序数据目录路径
    """
    base = get_base_dir()
    if hasattr(sys, '_MEIPASS'):
        app_data = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA')
        app_data_dir = os.path.join(app_data, 'XCAGI')
    else:
        app_data_dir = base
    
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir


def get_data_dir() -> str:
    """
    获取数据目录（用于存放数据库等数据文件）
    
    Returns:
        数据目录路径
    """
    return os.path.join(get_app_data_dir(), 'data')


def get_upload_dir() -> str:
    """
    获取上传文件目录
    
    Returns:
        上传文件目录路径
    """
    upload_dir = os.path.join(get_app_data_dir(), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_log_dir() -> str:
    """
    获取日志文件目录
    
    Returns:
        日志文件目录路径
    """
    log_dir = os.path.join(get_app_data_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_db_path(db_name: str = 'products.db') -> str:
    """
    获取数据库文件路径
    
    Args:
        db_name: 数据库文件名
        
    Returns:
        数据库文件完整路径
    """
    return os.path.join(get_data_dir(), db_name)


def ensure_dir(directory: str) -> str:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        目录路径
    """
    os.makedirs(directory, exist_ok=True)
    return directory
