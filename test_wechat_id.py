# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\FHD\XCAGI')

from app.db.session import get_db
from app.db.models import WechatContact

with get_db() as db:
    contact = db.query(WechatContact).filter(WechatContact.id == 1).first()
    if contact:
        print(f"Contact id=1:")
        print(f"  contact_name: {contact.contact_name}")
        print(f"  wechat_id: {contact.wechat_id}")
        print(f"  remark: {contact.remark}")
        print(f"  is_starred: {contact.is_starred}")
    else:
        print("Contact not found")