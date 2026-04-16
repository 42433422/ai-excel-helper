# -*- coding: utf-8 -*-
"""
找到联系人并打开微信对话框（不发送消息）。

用法:
  python open_wechat_chat.py "联系人备注或昵称"
  python open_wechat_chat.py 白龙马
  python open_wechat_chat.py --list          # 列出可用的联系人（从本地 DB 或专业版）
  python open_wechat_chat.py                 # 交互输入联系人名

依赖: 微信 PC 已启动并登录；wechat_cv 需 pywin32, pyautogui；可选 easyocr 提高搜索框定位。
"""
import os
import sys
import json
import argparse

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)


def list_contacts_from_db(limit=80):
    """从 wechat_db_read 或专业版 products.db 列联系人（若可用）。"""
    try:
        from wechat_db_read import get_contact_list_from_db
        out = get_contact_list_from_db()
        if out.get("success") and out.get("rows"):
            rows = out["rows"][:limit]
            return [r.get("nickName") or r.get("remark") or r.get("userName") or "" for r in rows]
    except Exception:
        pass
    # 专业版 wechat_contacts
    try:
        pro_db = os.path.join(os.path.dirname(_here), "AI助手", "products.db")
        if os.path.isfile(pro_db):
            import sqlite3
            conn = sqlite3.connect(pro_db)
            rows = conn.execute(
                "SELECT contact_name, wechat_id FROM wechat_contacts WHERE is_active = 1 ORDER BY contact_name LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [r[0] or r[1] or "" for r in rows if (r[0] or r[1])]
    except Exception:
        pass
    return []


def main():
    parser = argparse.ArgumentParser(description="找到联系人并打开微信对话框")
    parser.add_argument("contact", nargs="?", help="联系人备注或昵称（与微信里一致）")
    parser.add_argument("--list", "-l", action="store_true", help="列出可用联系人后退出")
    parser.add_argument("--no-ocr", action="store_true", help="不使用 OCR 定位搜索框，用固定坐标")
    args = parser.parse_args()

    if args.list:
        names = list_contacts_from_db()
        if not names:
            print("未找到联系人列表（可配置 wechat_db_key.json 或使用专业版同步的联系人）")
            return
        print("可用联系人（微信备注/昵称）：")
        for i, n in enumerate(names[:80], 1):
            print(f"  {i}. {n}")
        if len(names) > 80:
            print(f"  ... 共 {len(names)} 个")
        return

    contact_name = (args.contact or "").strip()
    if not contact_name:
        names = list_contacts_from_db(limit=100)
        if names:
            print("输入联系人名（或从下列选一个）：")
            for i, n in enumerate(names[:20], 1):
                print(f"  {i}. {n}")
        contact_name = input("联系人名: ").strip()
    if not contact_name:
        print("未输入联系人名")
        sys.exit(1)

    from wechat_cv_send import open_chat_by_cv
    use_ocr = not args.no_ocr
    result = open_chat_by_cv(contact_name, use_ocr=use_ocr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "success":
        sys.exit(2)


if __name__ == "__main__":
    main()
