"""
微信消息同步器 - 毫秒级轮询
实时监听微信数据库变化，同步消息到本地数据库
"""
import os
import sys
import time
import json
import hashlib
import sqlite3
import threading
import zstandard
from datetime import datetime
from collections import defaultdict
import functools

print = functools.partial(print, flush=True)

from config import load_config
from db_decryptor import WeChatDBDecryptor
from local_db import LocalMessageDB


class MessageSync:
    """微信消息同步器"""
    
    # 消息类型映射
    MSG_TYPES = {
        1: '文本',
        3: '图片',
        34: '语音',
        42: '名片',
        43: '视频',
        47: '表情',
        48: '位置',
        49: '链接/文件',
        50: '通话',
        10000: '系统',
        10002: '撤回',
    }
    
    def __init__(self):
        """初始化同步器"""
        self.config = load_config()
        self.db_dir = self.config.get('wechat_db_dir', '')
        self.keys_file = self.config.get('keys_file', 'all_keys.json')
        self.poll_interval = self.config.get('poll_interval_ms', 100) / 1000.0  # 转为秒
        self.batch_size = self.config.get('batch_size', 100)
        
        # 初始化解密器
        self.decryptor = None
        if os.path.exists(self.keys_file):
            self.decryptor = WeChatDBDecryptor(self.keys_file)
        
        # 初始化本地数据库
        self.local_db = LocalMessageDB(self.config.get('local_db_path', 'wechat_messages.db'))
        
        # 初始化 zstd 解压器
        self.zstd_dctx = zstandard.ZstdDecompressor()
        
        # 运行状态
        self.running = False
        self.session_state = {}  # 当前会话状态
        self.contact_cache = {}  # 联系人缓存
        self.username_db_map = {}  # username -> message_N.db 映射
        
        # 统计
        self.sync_count = 0
        self.last_sync_time = 0
        
    def _get_msg_type_name(self, msg_type):
        """获取消息类型名称"""
        base_type = msg_type % 4294967296 if msg_type > 4294967296 else msg_type
        return self.MSG_TYPES.get(base_type, f'类型({base_type})')
    
    def _decompress_content(self, content, ct_flag):
        """解压消息内容"""
        if not isinstance(content, bytes):
            return content or ''
        
        if ct_flag == 4:  # zstd 压缩
            try:
                return self.zstd_dctx.decompress(content).decode('utf-8', errors='replace')
            except:
                pass
        
        try:
            return content.decode('utf-8', errors='replace')
        except:
            return ''
    
    def load_contacts(self):
        """加载联系人信息"""
        if not self.decryptor or not self.db_dir:
            return
        
        contact_db = os.path.join(self.db_dir, 'contact', 'contact.db')
        if not os.path.exists(contact_db):
            return
        
        conn, tmp_path = self.decryptor.decrypt_to_memory_db(contact_db)
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT username, nick_name, remark FROM contact')
            for row in cursor.fetchall():
                username = row[0]
                self.contact_cache[username] = {
                    'nick_name': row[1] or '',
                    'remark': row[2] or ''
                }
                # 同时保存到本地数据库
                self.local_db.save_contact({
                    'username': username,
                    'nick_name': row[1] or '',
                    'remark': row[2] or ''
                })
            
            print(f"[*] 已加载 {len(self.contact_cache)} 个联系人")
        except Exception as e:
            print(f"[!] 加载联系人失败: {e}")
        finally:
            conn.close()
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def build_username_db_map(self):
        """构建 username -> message_N.db 映射"""
        if not self.decryptor or not self.db_dir:
            return
        
        self.username_db_map = {}
        
        # 检查 message_0.db 到 message_4.db
        for i in range(5):
            db_rel = os.path.join('message', f'message_{i}.db')
            db_path = os.path.join(self.db_dir, db_rel)
            
            if not os.path.exists(db_path):
                continue
            
            conn, tmp_path = self.decryptor.decrypt_to_memory_db(db_path)
            if not conn:
                continue
            
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT user_name FROM Name2Id')
                for row in cursor.fetchall():
                    username = row[0]
                    if username not in self.username_db_map:
                        self.username_db_map[username] = []
                    if db_rel not in self.username_db_map[username]:
                        self.username_db_map[username].append(db_rel)
            except Exception as e:
                pass
            finally:
                conn.close()
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        print(f"[*] 已映射 {len(self.username_db_map)} 个用户到消息数据库")
    
    def get_display_name(self, username):
        """获取显示名称"""
        if username in self.contact_cache:
            contact = self.contact_cache[username]
            return contact['remark'] or contact['nick_name'] or username
        return username
    
    def read_session_db(self):
        """读取会话数据库获取最新消息摘要"""
        if not self.decryptor or not self.db_dir:
            return {}
        
        session_db = os.path.join(self.db_dir, 'session', 'session.db')
        if not os.path.exists(session_db):
            return {}
        
        conn, tmp_path = self.decryptor.decrypt_to_memory_db(session_db)
        if not conn:
            return {}
        
        state = {}
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, unread_count, summary, last_timestamp,
                       last_msg_type, last_msg_sender, last_sender_display_name
                FROM SessionTable
                WHERE last_timestamp > 0
            ''')
            
            for row in cursor.fetchall():
                username = row[0]
                summary = row[2]
                
                # 解压摘要
                if isinstance(summary, bytes):
                    try:
                        summary = self.zstd_dctx.decompress(summary).decode('utf-8', errors='replace')
                    except:
                        summary = ''
                
                # 群消息格式: "wxid_xxx:\n内容" - 提取内容部分
                if summary and ':\n' in summary:
                    summary = summary.split(':\n', 1)[1]
                
                state[username] = {
                    'unread': row[1] or 0,
                    'summary': summary or '',
                    'timestamp': row[3] or 0,
                    'msg_type': row[4] or 0,
                    'sender': row[5] or '',
                    'sender_name': row[6] or '',
                }
        except Exception as e:
            print(f"[!] 读取会话数据库失败: {e}")
        finally:
            conn.close()
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        return state
    
    def fetch_messages_from_db(self, username, start_time, end_time):
        """
        从消息数据库获取指定时间范围内的消息
        :return: 消息列表
        """
        if not self.decryptor or username not in self.username_db_map:
            return []
        
        db_rels = self.username_db_map[username]
        table_name = f"Msg_{hashlib.md5(username.encode()).hexdigest()}"
        messages = []
        
        for db_rel in db_rels:
            db_path = os.path.join(self.db_dir, db_rel)
            if not os.path.exists(db_path):
                continue
            
            conn, tmp_path = self.decryptor.decrypt_to_memory_db(db_path)
            if not conn:
                continue
            
            try:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT local_id, create_time, local_type, message_content, WCDB_CT_message_content
                    FROM "{table_name}"
                    WHERE create_time >= ? AND create_time <= ?
                    ORDER BY create_time ASC
                ''', (start_time, end_time))
                
                for row in cursor.fetchall():
                    msg_type = row[2]
                    content = row[3]
                    ct_flag = row[4]
                    
                    # 解压内容
                    content = self._decompress_content(content, ct_flag)
                    
                    # 提取发送者(群消息)
                    sender_id = ''
                    sender_name = ''
                    is_group = '@chatroom' in username
                    
                    if is_group and content.startswith('wxid_'):
                        parts = content.split(':\n', 1)
                        if len(parts) == 2:
                            sender_id = parts[0]
                            sender_name = self.get_display_name(sender_id)
                            content = parts[1]
                    
                    msg_data = {
                        'username': username,
                        'chat_name': self.get_display_name(username),
                        'sender_id': sender_id,
                        'sender_name': sender_name,
                        'msg_type': msg_type,
                        'msg_type_name': self._get_msg_type_name(msg_type),
                        'content': content,
                        'create_time': row[1],
                        'create_time_str': datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d %H:%M:%S'),
                        'is_group': is_group,
                        'is_from_me': False,  # 需要进一步判断
                        'seq': row[0],
                    }
                    
                    messages.append(msg_data)
                
            except Exception as e:
                if 'no such table' not in str(e):
                    print(f"[!] 查询消息失败 {db_rel}: {e}")
            finally:
                conn.close()
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        return messages
    
    def sync_new_messages(self):
        """同步新消息"""
        current_state = self.read_session_db()
        
        if not self.session_state:
            # 首次运行，只记录状态
            self.session_state = current_state
            return 0
        
        new_messages = []
        
        for username, curr in current_state.items():
            prev = self.session_state.get(username)
            
            # 检测新消息: 时间戳变化或类型变化
            is_new = prev is None or curr['timestamp'] > prev['timestamp']
            is_type_changed = prev and curr['timestamp'] == prev['timestamp'] and curr['msg_type'] != prev.get('msg_type')
            
            if is_new or is_type_changed:
                # 确定时间范围
                if prev:
                    start_time = prev['timestamp'] - 5  # 稍微提前，避免遗漏
                else:
                    start_time = curr['timestamp'] - 5
                end_time = curr['timestamp'] + 5
                
                # 从消息数据库获取完整消息
                messages = self.fetch_messages_from_db(username, start_time, end_time)
                
                if messages:
                    new_messages.extend(messages)
                    print(f"[+] {self.get_display_name(username)}: {len(messages)} 条新消息")
                else:
                    # 如果无法从消息数据库获取，使用 session 的摘要
                    msg_data = {
                        'username': username,
                        'chat_name': self.get_display_name(username),
                        'sender_id': curr['sender'],
                        'sender_name': curr['sender_name'] or self.get_display_name(curr['sender']),
                        'msg_type': curr['msg_type'],
                        'msg_type_name': self._get_msg_type_name(curr['msg_type']),
                        'content': curr['summary'],
                        'create_time': curr['timestamp'],
                        'create_time_str': datetime.fromtimestamp(curr['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                        'is_group': '@chatroom' in username,
                        'is_from_me': False,
                        'seq': 0,
                    }
                    new_messages.append(msg_data)
        
        # 批量保存到本地数据库
        if new_messages:
            saved = self.local_db.save_messages_batch(new_messages)
            self.sync_count += saved
            
            # 更新同步状态
            for msg in new_messages:
                self.local_db.update_sync_status(
                    msg['username'],
                    msg['create_time'],
                    f"{msg['username']}_{msg['create_time']}"
                )
            
            return saved
        
        self.session_state = current_state
        return 0
    
    def run_once(self):
        """执行一次同步"""
        if not self.decryptor:
            print("[!] 未初始化解密器，请先提取密钥")
            return False
        
        try:
            saved = self.sync_new_messages()
            if saved > 0:
                self.last_sync_time = time.time()
            return True
        except Exception as e:
            print(f"[!] 同步失败: {e}")
            return False
    
    def run_continuous(self):
        """持续运行同步"""
        print("=" * 60)
        print("  微信消息同步服务")
        print("=" * 60)
        print(f"[*] 轮询间隔: {self.poll_interval*1000:.0f}ms")
        print(f"[*] 本地数据库: {self.config.get('local_db_path')}")
        print("[*] 按 Ctrl+C 停止\n")
        
        if not self.decryptor:
            print("[!] 错误: 未找到密钥文件，请先运行密钥提取")
            return
        
        # 加载联系人和映射
        print("[*] 加载联系人信息...")
        self.load_contacts()
        
        print("[*] 构建用户-数据库映射...")
        self.build_username_db_map()
        
        # 首次读取状态
        print("[*] 初始化会话状态...")
        self.session_state = self.read_session_db()
        print(f"[*] 跟踪 {len(self.session_state)} 个会话\n")
        
        self.running = True
        poll_count = 0
        
        try:
            while self.running:
                loop_start = time.time()
                
                # 执行同步
                saved = self.sync_new_messages()
                if saved > 0:
                    self.last_sync_time = time.time()
                    print(f"    本次同步: {saved} 条消息，总计: {self.sync_count} 条")
                
                poll_count += 1
                
                # 每100次轮询显示一次心跳
                if poll_count % 100 == 0:
                    stats = self.local_db.get_stats()
                    print(f"[*] 心跳 #{poll_count} | 数据库: {stats.get('total_messages', 0)} 条消息")
                
                # 计算下次轮询时间
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.poll_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print(f"\n[*] 同步服务已停止")
            print(f"[*] 总计同步: {self.sync_count} 条消息")
            print(f"[*] 轮询次数: {poll_count}")
    
    def get_stats(self):
        """获取同步统计"""
        return {
            'sync_count': self.sync_count,
            'last_sync_time': self.last_sync_time,
            'session_count': len(self.session_state),
            'contact_count': len(self.contact_cache),
        }


def main():
    """主函数"""
    sync = MessageSync()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'once':
            # 执行一次同步
            sync.run_once()
            
        elif cmd == 'stats':
            # 显示统计
            stats = sync.local_db.get_stats()
            print("=" * 60)
            print("  同步统计")
            print("=" * 60)
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
        elif cmd == 'search':
            # 搜索消息
            if len(sys.argv) > 2:
                keyword = sys.argv[2]
                results = sync.local_db.search_messages(keyword)
                print(f"[*] 搜索 '{keyword}' 找到 {len(results)} 条结果:")
                for msg in results[:20]:
                    print(f"  [{msg['create_time_str']}] {msg['chat_name']}: {msg['content'][:50]}")
            else:
                print("用法: python message_sync.py search <关键词>")
                
        elif cmd == 'recent':
            # 显示最近消息
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            messages = sync.local_db.get_recent_messages(limit=limit)
            print(f"[*] 最近 {len(messages)} 条消息:")
            for msg in messages:
                print(f"  [{msg['create_time_str']}] {msg['chat_name']}: {msg['content'][:50]}")
        else:
            print(f"未知命令: {cmd}")
            print("可用命令: once, stats, search, recent")
    else:
        # 持续运行
        sync.run_continuous()


if __name__ == '__main__':
    main()
