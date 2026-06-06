"""
一键安装 Windows 中文系统语音（Yunxi/Xiaoxiao/Huihui 等）。

TtsSetupBanner 对应前端入口："安装系统云希"。后端在本机派发一个 **UAC 提权** 的
PowerShell 进程去执行 ``Add-WindowsCapability``；用户在 UAC 对话框点"是"后，
安装过程由 PowerShell 窗口显示进度，完成后重启浏览器即可在
``window.speechSynthesis.getVoices()`` 中看到新语音。

设计要点：
- 仅支持 Windows：其他平台直接返回 501，便于前端回退到"打开设置手动安装"旧流程。
- 不要求 FastAPI 本身以管理员启动：通过 ``ShellExecuteW("runas", ...)`` 让子进程提权，
  父进程保持普通权限，避免整台后端暴露在提权上下文里。
- 使用 ``-EncodedCommand`` 传递 Base64-UTF16LE 脚本，彻底避免嵌套引号/中文路径被 cmd 解析破坏。
- 端点**不等待**安装完成：Windows Capability 下载体积较大（几十 MB 起），
  同步等会触发 Uvicorn 超时。立即返回 ``success=True``，由用户观察独立 PowerShell 窗口进度。
"""

from __future__ import annotations

import base64
import logging
import sys
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts-install"])


_PS_INSTALL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

Write-Host ''
Write-Host '==============================================='
Write-Host '  FHD 一键安装 Windows 中文神经网络语音'
Write-Host '==============================================='
Write-Host ''

try {
    $caps = Get-WindowsCapability -Online | Where-Object {
        ($_.Name -like 'Language.Speech~*zh-CN*' -or
         $_.Name -like 'Language.TextToSpeech~*zh-CN*' -or
         $_.Name -like 'Language.Basic~*zh-CN*') -and
        $_.State -ne 'Installed'
    }

    if ($null -eq $caps -or $caps.Count -eq 0) {
        Write-Host '✓ zh-CN 语音组件已是最新，无需安装。' -ForegroundColor Green
        Write-Host ''
        Write-Host '如果聊天顶栏仍提示未检测到云希/晓晓，可能原因：'
        Write-Host '  1) 当前浏览器缓存了旧的语音列表 → 关闭浏览器重新打开。'
        Write-Host '  2) 云希/晓晓 属于 Windows 11 22H2+ 附带的神经网络语音，老版本不含。'
        Write-Host '  3) 可在 设置 → 辅助功能 → 讲述人 → 添加自然语音 里补装。'
    } else {
        Write-Host ('待安装组件数：' + $caps.Count)
        Write-Host ''
        foreach ($cap in $caps) {
            Write-Host ('安装：' + $cap.Name) -ForegroundColor Cyan
            Add-WindowsCapability -Online -Name $cap.Name | Out-Null
        }
        Write-Host ''
        Write-Host '✓ 安装完成！请关闭 FHD 浏览器标签页后重新打开，即可听到系统云希/晓晓。' -ForegroundColor Green
    }
} catch {
    Write-Host ''
    Write-Host ('✗ 安装失败：' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ''
    Write-Host '建议改用 FHD 顶栏的 "下载离线包" 按钮，走本地 MMS-TTS 合成。'
}

Write-Host ''
Read-Host '按回车键关闭此窗口'
"""


def _encode_ps(script: str) -> str:
    """PowerShell -EncodedCommand 要求 UTF-16LE → Base64。"""
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


_LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}


def _is_local_request(request: Request) -> bool:
    """仅把请求方与后端在同一台机器时，才有条件弹 UAC。

    LAN 场景下，远端浏览器发的请求实际会在 "FHD 服务器" 上执行 ShellExecute，
    UAC 对话框会弹在服务器桌面（甚至是无人看管的主机），这显然不是用户期望的——
    他们想装的是自己这台电脑的系统语音。这时我们直接返回 501，前端自动回退到
    "打开 ms-settings:speech + 复制 PowerShell 命令" 的手动流程，用户在自己电脑上操作。
    """
    client = request.client
    host = (client.host if client else "") or ""
    return host in _LOCAL_IPS


@router.post("/api/tts/install-system-voice")
def install_system_voice(request: Request) -> Any:
    """触发 UAC 提权安装 Windows 中文语音包。

    Returns:
        {"success": True, "message": ...}  已弹出 UAC，由用户在弹出的 PowerShell 窗口观察进度
        {"success": False, "message": ...}  非 Windows / 远程客户端 / UAC 被拒 / ShellExecute 失败等
    """
    if not _is_local_request(request):
        return JSONResponse(
            {
                "success": False,
                "reason": "remote_client",
                "message": "检测到你是通过局域网访问 FHD，自动安装只能在运行服务端的本机进行。请在你自己的电脑上按说明手动安装。",
            },
            status_code=501,
        )

    if sys.platform != "win32":
        return JSONResponse(
            {
                "success": False,
                "platform": sys.platform,
                "message": "自动安装仅支持 Windows。请改用“下载离线包”以获得跨平台本地语音。",
            },
            status_code=501,
        )

    try:
        import ctypes

        encoded = _encode_ps(_PS_INSTALL_SCRIPT)
        args = f"-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"

        # ShellExecuteW 返回 >32 表示成功；==ERROR_CANCELLED(1223) 表示用户在 UAC 点了"否"。
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "powershell.exe",
            args,
            None,
            1,  # SW_SHOWNORMAL — 让用户看到安装进度
        )
        logger.info("ShellExecuteW(runas powershell) returned %s", ret)

        if int(ret) <= 32:
            code = int(ret)
            if code == 1223:
                msg = "已取消：用户在 UAC 对话框点了“否”。"
            else:
                msg = f"启动提权安装失败（ShellExecute={code}）。"
            return JSONResponse({"success": False, "code": code, "message": msg}, status_code=400)

        return {
            "success": True,
            "message": (
                "已弹出管理员授权。请在 UAC 对话框点“是”，"
                "然后在自动打开的 PowerShell 窗口观察安装进度，完成后重启浏览器即可。"
            ),
        }
    except Exception as exc:  # pragma: no cover — ctypes/系统调用异常
        logger.exception("install_system_voice failed")
        return JSONResponse(
            {"success": False, "message": f"无法启动安装：{exc}"},
            status_code=500,
        )
