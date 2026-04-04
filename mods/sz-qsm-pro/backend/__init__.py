"""
深圳奇士美定制 PRO Mod - 后端入口
"""

import logging
import shutil

logger = logging.getLogger(__name__)


def mod_init():
    """Mod 初始化函数"""
    logger.info("[奇士美 PRO] Mod初始化开始")
    try:
        from .services import (
            _phone_pywin32_installed,
            get_phone_agent_manager,
            on_shipment_created,
            on_product_imported,
        )
        manager = get_phone_agent_manager()
        if manager.is_available():
            logger.info("[奇士美 PRO] 电话业务员可用，可通过API启动")
        else:
            ch = str(getattr(manager, "_phone_channel", "") or "").strip().lower()
            if ch == "wechat" and not _phone_pywin32_installed():
                logger.warning(
                    "[奇士美 PRO] 电话业务员当前不可用：微信通道需要 pywin32（与 TTS/VB-Cable 无关）。"
                    "请在后端 Python 环境执行 pip install pywin32 后重启。"
                )
            elif ch == "adb" and not shutil.which("adb"):
                logger.warning(
                    "[奇士美 PRO] 电话业务员当前不可用：ADB 通道需要系统 PATH 中存在 adb。"
                )
            else:
                logger.warning("[奇士美 PRO] 电话业务员部分组件不可用")
        logger.info("[奇士美 PRO] Mod初始化完成")
    except Exception as e:
        logger.error(f"[奇士美 PRO] Mod初始化失败: {e}", exc_info=True)

# 4243342

