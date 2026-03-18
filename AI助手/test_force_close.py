#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的WPS强制关闭功能
"""

import os
import sys
import subprocess
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

def check_wps_processes():
    """
    检查当前运行的WPS进程
    """
    logger.info("🔍 检查当前运行的WPS进程...")
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq wps*.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            logger.info("当前运行的WPS进程:")
            logger.info(result.stdout)
            return "wps.exe" in result.stdout
        else:
            logger.info("未检测到WPS进程")
            return False
    except Exception as e:
        logger.error(f"检查WPS进程失败: {e}")
        return False

def test_force_close():
    """
    测试修复后的强制关闭功能
    """
    logger.info("🚀 开始测试修复后的WPS强制关闭功能...")
    
    # 1. 检查是否有WPS进程在运行
    has_wps = check_wps_processes()
    if not has_wps:
        logger.warning("⚠️ 未检测到WPS进程，无法测试强制关闭功能")
        return False
    
    # 2. 执行修复后的强制关闭逻辑
    logger.info("💥 执行强制关闭WPS进程...")
    
    try:
        # 扩展WPS相关进程列表
        processes = [
            "wps.exe", "et.exe", "wpp.exe",  # 主程序进程
            "wpscloudsvr.exe", "wpsnotify.exe",  # 后台服务
            "wpscenter.exe", "wpsapp.exe", "wpspro.exe",  # 其他可能的WPS进程
            "ksolaunch.exe", "ksodemo.exe", "wpsscan.exe",  # 相关工具进程
            "wpsunins.exe", "wpscrashreport.exe", "wpsupdatetask.exe"  # 更新和崩溃报告
        ]
        
        terminated_processes = []
        failed_processes = []
        
        for proc in processes:
            try:
                logger.info(f"尝试终止进程: {proc}")
                result = subprocess.run(
                    ["taskkill", "/IM", proc, "/F"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0:
                    logger.info(f"✅ 已强制终止进程: {proc}")
                    logger.debug(f"终止输出: {result.stdout.strip()}")
                    terminated_processes.append(proc)
                else:
                    logger.debug(f"❌ 进程 {proc} 未运行或终止失败: {result.stderr.strip()}")
                    failed_processes.append(proc)
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ 终止进程 {proc} 超时")
                failed_processes.append(proc)
            except Exception as e:
                logger.error(f"❌ 终止进程 {proc} 失败: {e}")
                failed_processes.append(proc)
        
        logger.info(f"进程终止结果: 成功 {len(terminated_processes)} 个, 失败 {len(failed_processes)} 个")
        if terminated_processes:
            logger.info(f"成功终止的进程: {', '.join(terminated_processes)}")
        
        # 增加等待时间，确保进程完全终止
        logger.info("⏳ 等待5秒让进程完全终止...")
        time.sleep(5)
        
        # 验证进程是否真正终止
        logger.info("🔍 验证WPS进程是否已终止...")
        remaining_processes = []
        
        for proc in processes:
            try:
                # 使用tasklist命令检查进程是否仍在运行
                check_result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {proc}"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                # 如果输出包含进程名，则表示进程仍在运行
                if proc in check_result.stdout:
                    remaining_processes.append(proc)
                    logger.warning(f"⚠️ 进程 {proc} 仍在运行")
                else:
                    logger.debug(f"✅ 进程 {proc} 已成功终止")
            except Exception as e:
                logger.debug(f"检查进程 {proc} 状态失败: {e}")
        
        if remaining_processes:
            logger.warning(f"⚠️ 测试结果: 仍有 {len(remaining_processes)} 个WPS进程在运行")
            return False
        else:
            logger.info("✅ 测试结果: 所有WPS进程已成功终止")
            return True
            
    except Exception as e:
        logger.error(f"强制终止进程失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_force_close()
    if success:
        logger.info("🎉 测试成功！修复后的强制关闭功能正常工作")
    else:
        logger.error("❌ 测试失败！强制关闭功能可能存在问题")
    sys.exit(0 if success else 1)
