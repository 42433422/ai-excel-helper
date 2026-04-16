# -*- coding: utf-8 -*-
"""
从「搜索联系人」到「获取聊天记录」全流程一键执行：
  1. 剪贴板写入联系人名 → 置顶微信 → 点击搜索框 → 粘贴
  2. 等待搜索结果 → 点击第一个联系人卡片进入聊天
  3. 二次确认：OCR 标题栏获取当前联系人名
  4. 获取当前可见聊天记录（OCR 聊天区域）

用法:
  python wechat_cv_full_flow.py [联系人名称] [最多消息行数]
  默认: 白龙马^_^李秋林  80
"""
import os
import sys
import json
import time

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from test_search_paste import test_search_box_paste
from wechat_cv_send import get_current_chat_contact_name, get_current_chat_messages


def run_full_flow(contact_name: str = "白龙马^_^李秋林", max_message_lines: int = 80):
    """
    执行全流程，返回 {"steps": {...}, "contact": {...}, "messages": {...}}。
    """
    result = {"steps": {}, "contact": None, "messages": None}

    # Step 1: 搜索并进入聊天
    try:
        test_search_box_paste(contact_name)
        result["steps"]["search_and_open_chat"] = "ok"
    except Exception as e:
        result["steps"]["search_and_open_chat"] = f"error: {e}"
        result["contact"] = {"success": False, "message": str(e)}
        result["messages"] = {"success": False, "message": str(e)}
        return result

    time.sleep(1.0)

    # Step 2: 二次确认当前联系人（标题栏 OCR）
    try:
        contact_result = get_current_chat_contact_name(use_ocr=True)
        result["contact"] = contact_result
        result["steps"]["get_contact"] = "ok" if contact_result.get("success") else contact_result.get("message", "fail")
    except Exception as e:
        result["contact"] = {"success": False, "message": str(e)}
        result["steps"]["get_contact"] = f"error: {e}"

    # Step 3: 获取聊天记录（聊天区域 OCR）
    try:
        messages_result = get_current_chat_messages(max_lines=max_message_lines, use_ocr=True)
        result["messages"] = messages_result
        result["steps"]["get_messages"] = "ok" if messages_result.get("success") else messages_result.get("message", "fail")
    except Exception as e:
        result["messages"] = {"success": False, "message": str(e)}
        result["steps"]["get_messages"] = f"error: {e}"

    return result


if __name__ == "__main__":
    contact = sys.argv[1] if len(sys.argv) > 1 else "白龙马^_^李秋林"
    max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 80
    out = run_full_flow(contact_name=contact, max_message_lines=max_lines)
    print(json.dumps(out, ensure_ascii=False, indent=2))
