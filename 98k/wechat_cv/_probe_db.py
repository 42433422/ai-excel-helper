# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'e:\FHD\wechat_cv')
from wechat_db_read import query_decrypted_or_encrypted

contact_db = r'C:\xwechat_files\wxid_bommxleja9kq22_22c5\db_storage\contact\contact.db'
msg_db = r'C:\xwechat_files\wxid_bommxleja9kq22_22c5\db_storage\message\message_0.db'
sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
for path, label in [(contact_db, 'contact'), (msg_db, 'msg')]:
    r = query_decrypted_or_encrypted(path, sql)
    print(label, 'success:', r.get('success'), 'msg:', (r.get('message') or '')[:60])
    if r.get('rows'):
        for row in r['rows'][:25]:
            print('  ', row.get('name'))
# get columns of first message-like table in message_0.db
r = query_decrypted_or_encrypted(msg_db, sql)
if r.get('success') and r.get('rows'):
    for row in r['rows']:
        t = row.get('name') or ''
        if 'message' in t.lower() or t == 'MSG':
            print('table', t)
            try:
                rr = query_decrypted_or_encrypted(msg_db, 'PRAGMA table_info([%s])' % t)
                if rr.get('rows'):
                    for c in rr['rows'][:25]:
                        print('  col', c.get('name'), c.get('type'))
            except Exception as e:
                print('  err', e)
            break
