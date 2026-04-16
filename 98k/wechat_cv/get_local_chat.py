# -*- coding: utf-8 -*-
"""
获取本地聊天：统一入口，支持「从本地数据库」或「从当前窗口 OCR」两种方式。

用法:
  # 从本地 DB 获取指定联系人的聊天（需已配置 wechat_db_key.json）
  python get_local_chat.py "联系人备注或昵称"
  python get_local_chat.py "白龙马^_^李秋林" --limit 30

  # 从当前微信窗口获取聊天（需微信在前台且已打开某聊天）
  python get_local_chat.py

  # 仅列联系人（DB）
  python get_local_chat.py --list

返回格式统一: {"source": "db"|"cv", "contact_name": "...", "messages": [{"role":"other"|"self","text":"..."}, ...], "success", "message"}
"""
import os
import sys
import json
import argparse

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)


def get_local_chat(contact_id_or_name=None, limit=50, only_other=True, wechat_data_dir=None):
    """
    获取本地聊天。优先用本地 DB；未传 contact 时用当前窗口 OCR。
    返回: {"source":"db"|"cv", "contact_name", "messages", "success", "message"}
    """
    if not wechat_data_dir:
        try:
            from wechat_db_read import get_default_wechat_data_dir
            wechat_data_dir = get_default_wechat_data_dir()
        except Exception:
            pass
        if not wechat_data_dir and os.path.isdir(r"C:\xwechat_files"):
            wechat_data_dir = r"C:\xwechat_files"

    # 1) 指定了联系人 → 用本地 DB
    if contact_id_or_name and contact_id_or_name.strip():
        from wechat_db_read import get_contact_and_messages_from_db
        out = get_contact_and_messages_from_db(
            contact_id_or_name.strip(),
            wechat_data_dir=wechat_data_dir,
            limit=limit,
            only_other=only_other,
        )
        out["source"] = "db"
        return out

    # 2) 未指定联系人 → 用当前窗口 OCR
    try:
        from wechat_cv_send import get_current_chat_contact_name, get_current_chat_messages
        contact_result = get_current_chat_contact_name(rect=None, use_ocr=True)
        msg_result = get_current_chat_messages(rect=None, max_lines=limit, use_ocr=True)
        contact_name = ""
        if contact_result.get("success") and contact_result.get("name"):
            contact_name = contact_result.get("name", "")
        messages = msg_result.get("rows", []) if msg_result.get("success") else []
        return {
            "source": "cv",
            "success": True,
            "contact_name": contact_name,
            "messages": messages,
            "message": "从当前窗口获取",
        }
    except Exception as e:
        return {
            "source": "cv",
            "success": False,
            "contact_name": "",
            "messages": [],
            "message": str(e),
        }


def list_contacts(wechat_data_dir=None):
    """列出本地联系人（仅 DB，需已配置 key）。"""
    if not wechat_data_dir:
        try:
            from wechat_db_read import get_default_wechat_data_dir
            wechat_data_dir = get_default_wechat_data_dir()
        except Exception:
            pass
        if not wechat_data_dir and os.path.isdir(r"C:\xwechat_files"):
            wechat_data_dir = r"C:\xwechat_files"
    from wechat_db_read import get_contact_list_from_db
    out = get_contact_list_from_db(wechat_data_dir=wechat_data_dir)
    return out


def main():
    ap = argparse.ArgumentParser(description="获取本地聊天（DB 或当前窗口 OCR）")
    ap.add_argument("contact", nargs="?", default=None, help="联系人备注/昵称，不传则取当前窗口")
    ap.add_argument("--limit", type=int, default=50, help="最多消息条数")
    ap.add_argument("--all", action="store_true", help="包含自己发送的消息（仅 DB）")
    ap.add_argument("--list", action="store_true", help="仅列联系人（DB）")
    ap.add_argument("--dir", default=None, help="微信数据目录，如 C:\\xwechat_files")
    args = ap.parse_args()

    if args.list:
        out = list_contacts(wechat_data_dir=args.dir)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("success") else 1

    out = get_local_chat(
        contact_id_or_name=args.contact,
        limit=args.limit,
        only_other=not args.all,
        wechat_data_dir=args.dir,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
