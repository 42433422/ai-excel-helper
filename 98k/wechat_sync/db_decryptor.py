"""
微信数据库解密模块
复用 wechat-decrypt 的核心解密逻辑
"""
import hashlib
import struct
import os
import sys
import json
import hmac as hmac_mod
from Crypto.Cipher import AES
import functools

print = functools.partial(print, flush=True)

# SQLCipher 4 参数
PAGE_SZ = 4096
KEY_SZ = 32
SALT_SZ = 16
IV_SZ = 16
HMAC_SZ = 64
RESERVE_SZ = 80  # IV(16) + HMAC(64)
SQLITE_HDR = b'SQLite format 3\x00'


class WeChatDBDecryptor:
    """微信数据库解密器"""
    
    def __init__(self, keys_file):
        """
        初始化解密器
        :param keys_file: 密钥文件路径 (JSON格式)
        """
        self.keys = self._load_keys(keys_file)
        
    def _load_keys(self, keys_file):
        """加载密钥文件"""
        if not os.path.exists(keys_file):
            raise FileNotFoundError(f"密钥文件不存在: {keys_file}")
        
        with open(keys_file, 'r', encoding='utf-8') as f:
            keys = json.load(f)
        
        # 移除元数据字段
        return {k: v for k, v in keys.items() if not k.startswith('_')}
    
    def _derive_mac_key(self, enc_key, salt):
        """从 enc_key 派生 HMAC 密钥"""
        mac_salt = bytes(b ^ 0x3a for b in salt)
        return hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, dklen=KEY_SZ)
    
    def _decrypt_page(self, enc_key, page_data, pgno):
        """解密单个页面"""
        iv = page_data[PAGE_SZ - RESERVE_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
        
        if pgno == 1:
            encrypted = page_data[SALT_SZ : PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(enc_key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted)
            page = bytearray(SQLITE_HDR + decrypted + b'\x00' * RESERVE_SZ)
            return bytes(page)
        else:
            encrypted = page_data[:PAGE_SZ - RESERVE_SZ]
            cipher = AES.new(enc_key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted)
            return decrypted + b'\x00' * RESERVE_SZ
    
    def get_key_for_db(self, db_rel_path):
        """
        获取指定数据库的密钥
        :param db_rel_path: 数据库相对路径 (如 "session/session.db")
        :return: enc_key bytes 或 None
        """
        # 尝试多种路径格式
        variants = [
            db_rel_path,
            db_rel_path.replace('\\', '/'),
            db_rel_path.replace('/', '\\'),
            db_rel_path.replace('/', os.sep),
        ]
        
        for variant in variants:
            if variant in self.keys:
                key_info = self.keys[variant]
                return bytes.fromhex(key_info["enc_key"])
        return None
    
    def decrypt_database(self, db_path, out_path=None):
        """
        解密整个数据库文件
        :param db_path: 加密数据库路径
        :param out_path: 输出路径 (默认在内存中返回)
        :return: (解密后的数据 bytes, 页面数) 或 (None, 0) 如果失败
        """
        # 获取相对路径用于查找密钥
        db_rel_path = os.path.basename(os.path.dirname(db_path))
        parent_dir = os.path.basename(os.path.dirname(os.path.dirname(db_path)))
        rel_key = os.path.join(parent_dir, db_rel_path).replace('/', os.sep)
        
        enc_key = self.get_key_for_db(rel_key)
        if not enc_key:
            # 尝试其他格式
            for key in self.keys.keys():
                if db_rel_path in key or key.endswith(os.path.basename(db_path)):
                    enc_key = bytes.fromhex(self.keys[key]["enc_key"])
                    break
        
        if not enc_key:
            print(f"[!] 未找到密钥: {db_path}")
            return None, 0
        
        # 读取并解密
        file_size = os.path.getsize(db_path)
        total_pages = file_size // PAGE_SZ
        if file_size % PAGE_SZ != 0:
            total_pages += 1
        
        with open(db_path, 'rb') as fin:
            page1 = fin.read(PAGE_SZ)
        
        if len(page1) < PAGE_SZ:
            print(f"[!] 文件太小: {db_path}")
            return None, 0
        
        # 验证 page 1 HMAC
        salt = page1[:SALT_SZ]
        mac_key = self._derive_mac_key(enc_key, salt)
        p1_hmac_data = page1[SALT_SZ : PAGE_SZ - RESERVE_SZ + IV_SZ]
        p1_stored_hmac = page1[PAGE_SZ - HMAC_SZ : PAGE_SZ]
        hm = hmac_mod.new(mac_key, p1_hmac_data, hashlib.sha512)
        hm.update(struct.pack('<I', 1))
        
        if hm.digest() != p1_stored_hmac:
            print(f"[!] HMAC 验证失败: {db_path}")
            return None, 0
        
        # 解密所有页面
        chunks = []
        with open(db_path, 'rb') as fin:
            for pgno in range(1, total_pages + 1):
                page = fin.read(PAGE_SZ)
                if len(page) < PAGE_SZ:
                    if len(page) > 0:
                        page = page + b'\x00' * (PAGE_SZ - len(page))
                    else:
                        break
                decrypted = self._decrypt_page(enc_key, page, pgno)
                chunks.append(decrypted)
        
        decrypted_data = b''.join(chunks)
        
        # 如果指定了输出路径，写入文件
        if out_path:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'wb') as f:
                f.write(decrypted_data)
        
        return decrypted_data, total_pages
    
    def decrypt_to_memory_db(self, db_path):
        """
        解密数据库到内存中的 SQLite 连接
        :param db_path: 加密数据库路径
        :return: (sqlite3连接, 临时文件路径) 或 (None, None)
        """
        import sqlite3
        import tempfile
        
        decrypted_data, pages = self.decrypt_database(db_path)
        if not decrypted_data:
            return None, None
        
        # 创建临时文件
        fd, tmp_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        with open(tmp_path, 'wb') as f:
            f.write(decrypted_data)
        
        try:
            conn = sqlite3.connect(tmp_path)
            conn.row_factory = sqlite3.Row
            return conn, tmp_path
        except Exception as e:
            print(f"[!] SQLite 连接失败: {e}")
            os.unlink(tmp_path)
            return None, None


def decrypt_all_databases(keys_file, db_dir, out_dir):
    """
    一键解密所有微信数据库
    :param keys_file: 密钥文件路径
    :param db_dir: 微信数据库目录
    :param out_dir: 输出目录
    :return: (成功数, 失败数)
    """
    decryptor = WeChatDBDecryptor(keys_file)
    
    # 收集所有 .db 文件
    db_files = []
    for root, dirs, files in os.walk(db_dir):
        for f in files:
            if f.endswith('.db') and not f.endswith('-wal') and not f.endswith('-shm'):
                path = os.path.join(root, f)
                rel = os.path.relpath(path, db_dir)
                db_files.append((rel, path))
    
    print(f"[*] 找到 {len(db_files)} 个数据库文件")
    
    success = 0
    failed = 0
    
    for rel, path in db_files:
        out_path = os.path.join(out_dir, rel)
        print(f"[*] 解密: {rel} ...", end=" ")
        
        data, pages = decryptor.decrypt_database(path, out_path)
        if data:
            print(f"OK ({pages}页)")
            success += 1
        else:
            print("FAILED")
            failed += 1
    
    return success, failed
