# -*- coding: utf-8 -*-
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, r'E:\FHD\XCAGI')

from app.db.session import get_db
from app.db.models import WechatContact
from app.utils.path_utils import get_resource_path

with get_db() as db:
    contact = db.query(WechatContact).filter(WechatContact.id == 1).first()
    if contact:
        wechat_id = contact.wechat_id or ""
        print(f"Contact wechat_id: '{wechat_id}'")

        msg_db_path = r'E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db'
        print(f"msg_db_path: {msg_db_path}, exists: {os.path.exists(msg_db_path)}")

        # Test import directly
        sys.path.insert(0, get_resource_path("wechat-decrypt"))
        print(f"Path before import: {sys.path[:3]}")
        try:
            from mcp_server import _decompress_content
            print(f"_decompress_content imported: {_decompress_content}")

            # Test decompress
            import sqlite3
            conn = sqlite3.connect(msg_db_path)
            cur = conn.cursor()
            tbl = 'Msg_89707d4abce0cecdca50a8d0718b152b'
            cur.execute(f"SELECT message_content, WCDB_CT_message_content FROM [{tbl}] WHERE real_sender_id = 98 LIMIT 2")
            for row in cur.fetchall():
                raw, ct = row
                print(f"\nraw type={type(raw)}, ct={ct}")
                result = _decompress_content(raw, ct)
                print(f"decompress result type={type(result)}, result={repr(result[:50]) if result else None}")
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Contact not found")