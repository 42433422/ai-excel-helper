# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\FHD\XCAGI')
from app.db.session import get_db
from app.db.models import WechatContactContext

with get_db() as db:
    ctx = db.query(WechatContactContext).filter(
        WechatContactContext.contact_id == 1
    ).first()
    if ctx:
        print(f"Deleting context for contact_id=1")
        db.delete(ctx)
        db.commit()
        print("Deleted successfully")
    else:
        print("No context found for contact_id=1")