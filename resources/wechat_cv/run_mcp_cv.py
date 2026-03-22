# -*- coding: utf-8 -*-
"""
纯 CV 版微信 MCP 服务：通过截图+OCR 理解屏幕，用点击/粘贴发送，不依赖 UI 控件树。
运行: python run_mcp_cv.py  （需已安装 mcp, pywin32, pyautogui, Pillow；可选 easyocr）
Cursor MCP 配置示例:
  "wechat-cv": {
    "command": "C:\\Program Files\\Python311\\python.exe",
    "args": ["E:\\FHD\\wechat_cv\\run_mcp_cv.py"]
  }
"""
import asyncio
import json
import sys
import os

# 保证可导入同目录下的 wechat_cv_send
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


def _send_current(message: str, delay: float = 1.2):
    from wechat_cv_send import send_to_current_chat_by_cv
    return send_to_current_chat_by_cv(message, delay=delay, use_ocr=True)


def _send_to_friend(to_user: str, message: str, delay: float = 1.2):
    from wechat_cv_send import search_and_send_by_cv
    return search_and_send_by_cv(to_user, message, delay=delay, use_ocr=True)


def _get_current_contact():
    from wechat_cv_send import get_current_chat_contact_name
    return get_current_chat_contact_name(rect=None, use_ocr=True)


def _get_chat_messages(max_lines: int = 80):
    from wechat_cv_send import get_current_chat_messages
    return get_current_chat_messages(rect=None, max_lines=max_lines, use_ocr=True)


def _db_list_contacts(wechat_data_dir=None):
    from wechat_db_read import get_contact_list_from_db
    return get_contact_list_from_db(wechat_data_dir=wechat_data_dir)


def _db_get_contact_messages(contact_id_or_name: str, limit=50, only_other=True):
    from wechat_db_read import get_contact_and_messages_from_db
    return get_contact_and_messages_from_db(contact_id_or_name, limit=limit, only_other=only_other)


async def main():
    server = Server("WeChatCV")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="wechat_cv_send_current",
                description="纯CV：向「当前已打开的聊天」发送消息。请先手动打开与对方的聊天并保持微信在前台。不依赖UI控件，用截图+点击+粘贴。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "要发送的内容"},
                        "delay": {"type": "number", "description": "粘贴后到发送前的延迟(秒)", "default": 1.2},
                    },
                    "required": ["message"],
                },
            ),
            Tool(
                name="wechat_cv_send_to_friend",
                description="纯CV：通过搜索框找好友并发送消息。用截图+OCR定位搜索/发送，不依赖UI控件。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to_user": {"type": "string", "description": "好友备注或昵称"},
                        "message": {"type": "string", "description": "要发送的内容"},
                        "delay": {"type": "number", "description": "发送前延迟(秒)", "default": 1.2},
                    },
                    "required": ["to_user", "message"],
                },
            ),
            Tool(
                name="wechat_cv_get_current_contact",
                description="纯CV：获取当前聊天窗口左上角显示的联系人名称（标题栏OCR二次确认）。需微信在前台且已进入某聊天。",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="wechat_cv_get_chat_messages",
                description="纯CV：对当前聊天消息区域做OCR，尽力获取可见的聊天文字（按行）。需微信在前台且已进入某聊天。",
                inputSchema={
                    "type": "object",
                    "properties": {"max_lines": {"type": "number", "description": "最多返回行数", "default": 80}},
                    "required": [],
                },
            ),
            Tool(
                name="wechat_db_list_contacts",
                description="用本地数据库：列出微信联系人（备注/昵称/微信ID）。无需打开微信窗口，需已配置 wechat_db_key.json 解密。优先使用此方式替代「当前聊天」前先确认联系人。",
                inputSchema={
                    "type": "object",
                    "properties": {"wechat_data_dir": {"type": "string", "description": "可选，微信数据目录，不传则用默认 Documents\\WeChat Files\\<ID>"}},
                    "required": [],
                },
            ),
            Tool(
                name="wechat_db_get_contact_messages",
                description="用本地数据库：根据联系人（微信ID/备注/昵称）直接获取「联系人名称 + 对方消息列表」。无需打开微信、无需OCR，替代 wechat_cv_get_current_contact + wechat_cv_get_chat_messages 或完整流程。需已配置 wechat_db_key.json。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id_or_name": {"type": "string", "description": "联系人：微信ID、备注或昵称"},
                        "limit": {"type": "number", "description": "最多返回条数", "default": 50},
                        "only_other": {"type": "boolean", "description": "是否只返回对方消息", "default": True},
                    },
                    "required": ["contact_id_or_name"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "wechat_cv_send_current":
                msg = arguments.get("message", "")
                delay = float(arguments.get("delay", 1.2))
                out = _send_current(msg, delay=delay)
            elif name == "wechat_cv_send_to_friend":
                to_user = arguments.get("to_user", "")
                msg = arguments.get("message", "")
                delay = float(arguments.get("delay", 1.2))
                out = _send_to_friend(to_user, msg, delay=delay)
            elif name == "wechat_cv_get_current_contact":
                out = _get_current_contact()
            elif name == "wechat_cv_get_chat_messages":
                max_lines = int(arguments.get("max_lines", 80))
                out = _get_chat_messages(max_lines=max_lines)
            elif name == "wechat_db_list_contacts":
                out = _db_list_contacts(wechat_data_dir=arguments.get("wechat_data_dir"))
            elif name == "wechat_db_get_contact_messages":
                out = _db_get_contact_messages(
                    contact_id_or_name=arguments.get("contact_id_or_name", ""),
                    limit=int(arguments.get("limit", 50)),
                    only_other=arguments.get("only_other", True),
                )
            else:
                out = {"status": "error", "message": f"未知工具: {name}"}
            return [TextContent(type="text", text=json.dumps(out, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
