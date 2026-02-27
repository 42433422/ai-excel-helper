#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WPS窗口强制关闭脚本

用于强制关闭WPS相关进程
"""

import os
import sys
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def force_close_wps():
    """
    强制关闭WPS相关进程
    """
    logger.info("🚀 开始强制关闭WPS...")
    
    # 尝试使用不同的方法关闭WPS
    methods = [
        ("taskkill命令", kill_wps_with_taskkill),
        ("wmic命令", kill_wps_with_wmic),
        ("powershell命令", kill_wps_with_powershell),
    ]
    
    success = False
    for method_name, method_func in methods:
        logger.info(f"尝试方法: {method_name}")
        try:
            if method_func():
                logger.info(f"✅ {method_name} 成功关闭WPS")
                success = True
                break
            else:
                logger.warning(f"⚠️ {method_name} 未能关闭WPS")
        except Exception as e:
            logger.error(f"❌ {method_name} 执行失败: {e}")
    
    if success:
        # 等待2秒让进程完全终止
        time.sleep(2)
        # 验证是否真正关闭
        if not is_wps_running():
            logger.info("✅ WPS已完全关闭")
            return True
        else:
            logger.warning("⚠️ WPS可能仍在运行")
            return False
    else:
        logger.error("❌ 所有方法都未能关闭WPS")
        return False

def kill_wps_with_taskkill():
    """
    使用taskkill命令关闭WPS
    """
    import subprocess
    
    # 查找WPS相关进程
    processes = [
        "wps.exe",
        "wpp.exe",
        "et.exe",
        "wpscenter.exe",
        "wpscloudsvr.exe",
        "wpsnotify.exe",
    ]
    
    success = False
    for proc in processes:
        try:
            # 先尝试优雅终止
            result = subprocess.run(
                ["taskkill", "/IM", proc, "/F"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"已终止进程: {proc}")
                success = True
            else:
                logger.debug(f"终止 {proc} 失败: {result.stderr}")
        except Exception as e:
            logger.debug(f"执行taskkill失败: {e}")
    
    return success

def kill_wps_with_wmic():
    """
    使用wmic命令关闭WPS
    """
    import subprocess
    
    try:
        # 查找包含WPS的进程
        result = subprocess.run(
            ["wmic", "process", "where", "name like '%wps%' or name like '%et%' or name like '%wpp%'", "call", "terminate"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("wmic命令执行成功")
            return True
        else:
            logger.debug(f"wmic执行失败: {result.stderr}")
            return False
    except Exception as e:
        logger.debug(f"执行wmic失败: {e}")
        return False

def kill_wps_with_powershell():
    """
    使用powershell命令关闭WPS
    """
    import subprocess
    
    try:
        # 使用PowerShell命令查找并终止WPS进程
        ps_command = '''
        Get-Process | Where-Object {$_.Name -like "*wps*" -or $_.Name -like "*et*" -or $_.Name -like "*wpp*"} | Stop-Process -Force
        '''
        
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("PowerShell命令执行成功")
            return True
        else:
            logger.debug(f"PowerShell执行失败: {result.stderr}")
            return False
    except Exception as e:
        logger.debug(f"执行PowerShell失败: {e}")
        return False

def is_wps_running():
    """
    检查WPS是否仍在运行
    """
    import subprocess
    
    try:
        # 使用tasklist命令检查进程
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq wps.exe", "/FI", "IMAGENAME eq et.exe", "/FI", "IMAGENAME eq wpp.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # 检查输出中是否包含WPS进程
        return "wps.exe" in result.stdout or "et.exe" in result.stdout or "wpp.exe" in result.stdout
    except Exception as e:
        logger.debug(f"检查WPS运行状态失败: {e}")
        return False

if __name__ == "__main__":
    force_close_wps()