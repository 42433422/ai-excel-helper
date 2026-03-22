# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')

from app.db.session import get_db
from app.db.models import WechatContact
from app.utils.path_utils import get_resource_path
from app.routes.wechat_contacts import _query_messages_from_hash_tables, _ensure_decrypted_db

with get_db() as db:
    contact = db.query(WechatContact).filter(WechatContact.id == 1).first()
    if contact:
        wechat_id = contact.wechat_id or ""
        print(f"Contact wechat_id: '{wechat_id}'")

        sync_result = _ensure_decrypted_db()
        print(f"Sync result: {sync_result}")

        decrypted_msg_dir = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message")
        msg_db_path = os.path.join(decrypted_msg_dir, "message_0.db")
        print(f"msg_db_path: {msg_db_path}, exists: {os.path.exists(msg_db_path)}")

        messages = _query_messages_from_hash_tables(msg_db_path, wechat_id, limit=50, search_in_content=True)
        print(f"Returned {len(messages)} messages")

        for i, msg in enumerate(messages[:3]):
            print(f"\n[{i}] {msg['role']}: {repr(msg['text'][:80])}")
    else:
        print("Contact not found")