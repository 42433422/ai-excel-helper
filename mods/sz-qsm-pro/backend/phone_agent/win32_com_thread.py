"""
Windows COM 公寓初始化：供采音（WASAPI）、窗口监控等工作线程使用。

错误使用 CoInitialize/CoUninitialize（例如线程已初始化却仍 Uninit，或 Uninit 时仍有
IAudioClient 等 COM 对象未释放）易导致堆损坏。此处统一：

- 使用 CoInitializeEx(COINIT_APARTMENTTHREADED)，与多数音频/UI COM 组件期望的 STA 一致；
- 若返回 RPC_E_CHANGED_MODE（本线程已由其它代码初始化 COM），则不再调用 CoUninitialize，
  避免破坏公寓引用计数。
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

# RPC_E_CHANGED_MODE — 线程上 COM 已按其它模式初始化，本次调用未增加引用计数
RPC_E_CHANGED_MODE = -2147417850  # 0x80010106


def is_pythoncom_available() -> bool:
    try:
        import pythoncom  # noqa: F401

        return True
    except ImportError:
        return False


def com_init_apartment_thread() -> bool:
    """
    在当前线程初始化 COM（STA）。

    Returns:
        True 表示本次调用成功增加了本线程的 COM 初始化计数，线程退出前必须调用
        com_uninit_apartment_thread(True) 配对；
        False 表示未增加计数（未安装 pywin32、RPC_E_CHANGED_MODE、或其它失败），
        调用方不得对本次结果执行 CoUninitialize。
    """
    try:
        import pythoncom
    except ImportError:
        return False
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        return True
    except Exception as e:
        hr = getattr(e, "hresult", None)
        try:
            if hr is not None and int(hr) == RPC_E_CHANGED_MODE:
                return False
        except (TypeError, ValueError):
            pass
        logger.debug("com_init_apartment_thread: %s", e)
        return False


def com_uninit_apartment_thread(initialized_here: bool) -> None:
    if not initialized_here:
        return
    try:
        import pythoncom

        pythoncom.CoUninitialize()
    except Exception:
        pass
