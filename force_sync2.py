# -*- coding: utf-8 -*-
import sys, os, glob, json, shutil
sys.path.insert(0, r'E:\FHD\XCAGI\resources\wechat-decrypt')
from config import load_config
from key_utils import get_key_info, strip_key_metadata
from decrypt_db import decrypt_database

cfg = load_config()
db_dir = cfg.get('db_dir')
raw_db_dir = r'E:\FHD\XCAGI\resources\wechat-decrypt\raw_db'
decrypted_dir = cfg.get('decrypted_dir')
raw_msg_dir = os.path.join(raw_db_dir, 'message')
src_msg = os.path.join(db_dir, 'message')
os.makedirs(raw_msg_dir, exist_ok=True)
os.makedirs(os.path.join(decrypted_dir, 'message'), exist_ok=True)

print('=== 强制复制和解密 ===')

# 删除旧文件
for f in glob.glob(os.path.join(raw_msg_dir, '*')):
    os.remove(f)
for f in glob.glob(os.path.join(decrypted_dir, 'message', '*')):
    if not f.endswith('.gitkeep'):
        os.remove(f)

# 复制
copy_count = 0
for f in glob.glob(os.path.join(src_msg, '*.db')):
    if f.endswith('-wal') or f.endswith('-shm'):
        continue
    shutil.copy2(f, raw_msg_dir)
    copy_count += 1
    print(f'复制: {os.path.basename(f)}')

print(f'复制完成: {copy_count} 个文件')

# 解密
with open(cfg.get('keys_file'), 'r', encoding='utf-8') as f:
    keys = json.load(f)
keys = strip_key_metadata(keys)

decrypt_count = 0
for raw_path in glob.glob(os.path.join(raw_msg_dir, '*.db')):
    rel = os.path.relpath(raw_path, raw_msg_dir)
    dec_path = os.path.join(decrypted_dir, 'message', rel)
    key_info = get_key_info(keys, os.path.join('message', rel))
    if key_info:
        result = decrypt_database(raw_path, dec_path, bytes.fromhex(key_info['enc_key']))
        if result:
            decrypt_count += 1
            print(f'解密: {rel}')

print(f'解密完成: {decrypt_count} 个文件')
