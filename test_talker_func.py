# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r'E:\FHD\XCAGI')
from app.utils.path_utils import get_resource_path
from app.routes.wechat_contacts import _query_messages_from_hash_tables

msg_db = os.path.join(get_resource_path("wechat-decrypt"), "decrypted", "message", "message_0.db")
print(f"DB exists: {os.path.exists(msg_db)}")

wechat_id = 'wxid_tfxzqdqt87oa22'
print(f"Searching for: {wechat_id}")

messages = _query_messages_from_hash_tables(msg_db, wechat_id, limit=50, search_in_content=True)
print(f"Found {len(messages)} messages")
for i, msg in enumerate(messages[:5]):
    print(f"\n[{i}] role={msg['role']}: {repr(msg['text'][:80])}")