"""
本地消息数据库管理模块
用于存储同步的微信消息
"""
import sqlite3
import os
import hashlib
from datetime import datetime


class LocalMessageDB:
    """本地消息数据库管理器"""
    
    def __init__(self, db_path):
        """
        初始化本地数据库
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # 创建消息表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_id TEXT UNIQUE,           -- 消息唯一标识 (username_timestamp_seq)
                username TEXT NOT NULL,        -- 聊天对象ID
                chat_name TEXT,                -- 聊天对象名称(群名/联系人备注)
                sender_id TEXT,                -- 发送者ID
                sender_name TEXT,              -- 发送者名称
                msg_type INTEGER,              -- 消息类型 (1=文本, 3=图片, etc.)
                msg_type_name TEXT,            -- 消息类型名称
                content TEXT,                  -- 消息内容
                content_hash TEXT,             -- 内容哈希(用于去重)
                create_time INTEGER,           -- 消息创建时间戳
                create_time_str TEXT,          -- 格式化时间字符串
                is_group INTEGER DEFAULT 0,    -- 是否群聊
                is_from_me INTEGER DEFAULT 0,  -- 是否自己发送
                extra_data TEXT,               -- 额外数据(JSON格式)
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 同步时间
                UNIQUE(username, create_time, content_hash)
            )
        ''')
        
        # 创建索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(create_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_username ON messages(username)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_type ON messages(msg_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_synced ON messages(synced_at)')
        
        # 创建联系人表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,          -- 微信ID
                nick_name TEXT,                -- 昵称
                remark TEXT,                   -- 备注名
                avatar TEXT,                   -- 头像路径
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建同步状态表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,          -- 聊天对象
                last_msg_time INTEGER,         -- 最后同步的消息时间
                last_msg_id TEXT,              -- 最后同步的消息ID
                sync_count INTEGER DEFAULT 0,  -- 同步消息数
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建系统配置表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        print(f"[*] 本地数据库已初始化: {self.db_path}")
    
    def _generate_msg_id(self, username, timestamp, seq=0):
        """生成消息唯一ID"""
        return f"{username}_{timestamp}_{seq}"
    
    def _hash_content(self, content):
        """计算内容哈希"""
        if not content:
            return ""
        return hashlib.md5(str(content).encode('utf-8')).hexdigest()[:16]
    
    def save_message(self, msg_data):
        """
        保存单条消息
        :param msg_data: 消息字典
        :return: 是否成功
        """
        try:
            username = msg_data.get('username', '')
            timestamp = msg_data.get('create_time', 0)
            content = msg_data.get('content', '')
            
            msg_id = self._generate_msg_id(username, timestamp, msg_data.get('seq', 0))
            content_hash = self._hash_content(content)
            
            self.cursor.execute('''
                INSERT OR IGNORE INTO messages 
                (msg_id, username, chat_name, sender_id, sender_name, 
                 msg_type, msg_type_name, content, content_hash, 
                 create_time, create_time_str, is_group, is_from_me, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                msg_id,
                username,
                msg_data.get('chat_name', ''),
                msg_data.get('sender_id', ''),
                msg_data.get('sender_name', ''),
                msg_data.get('msg_type', 0),
                msg_data.get('msg_type_name', ''),
                content,
                content_hash,
                timestamp,
                msg_data.get('create_time_str', ''),
                1 if msg_data.get('is_group') else 0,
                1 if msg_data.get('is_from_me') else 0,
                msg_data.get('extra_data', '{}')
            ))
            
            self.conn.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            print(f"[!] 保存消息失败: {e}")
            return False
    
    def save_messages_batch(self, messages):
        """
        批量保存消息
        :param messages: 消息列表
        :return: 成功保存的数量
        """
        if not messages:
            return 0
        
        saved = 0
        try:
            for msg_data in messages:
                username = msg_data.get('username', '')
                timestamp = msg_data.get('create_time', 0)
                content = msg_data.get('content', '')
                
                msg_id = self._generate_msg_id(username, timestamp, msg_data.get('seq', 0))
                content_hash = self._hash_content(content)
                
                self.cursor.execute('''
                    INSERT OR IGNORE INTO messages 
                    (msg_id, username, chat_name, sender_id, sender_name, 
                     msg_type, msg_type_name, content, content_hash, 
                     create_time, create_time_str, is_group, is_from_me, extra_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    msg_id,
                    username,
                    msg_data.get('chat_name', ''),
                    msg_data.get('sender_id', ''),
                    msg_data.get('sender_name', ''),
                    msg_data.get('msg_type', 0),
                    msg_data.get('msg_type_name', ''),
                    content,
                    content_hash,
                    timestamp,
                    msg_data.get('create_time_str', ''),
                    1 if msg_data.get('is_group') else 0,
                    1 if msg_data.get('is_from_me') else 0,
                    msg_data.get('extra_data', '{}')
                ))
                
                if self.cursor.rowcount > 0:
                    saved += 1
            
            self.conn.commit()
            return saved
            
        except Exception as e:
            print(f"[!] 批量保存消息失败: {e}")
            self.conn.rollback()
            return saved
    
    def update_sync_status(self, username, last_msg_time, last_msg_id=None):
        """更新同步状态"""
        try:
            self.cursor.execute('''
                INSERT INTO sync_status (username, last_msg_time, last_msg_id, sync_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(username) DO UPDATE SET
                    last_msg_time = excluded.last_msg_time,
                    last_msg_id = excluded.last_msg_id,
                    sync_count = sync_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            ''', (username, last_msg_time, last_msg_id))
            self.conn.commit()
        except Exception as e:
            print(f"[!] 更新同步状态失败: {e}")
    
    def get_last_sync_time(self, username):
        """获取指定聊天的最后同步时间"""
        try:
            self.cursor.execute(
                'SELECT last_msg_time FROM sync_status WHERE username = ?',
                (username,)
            )
            row = self.cursor.fetchone()
            return row['last_msg_time'] if row else 0
        except:
            return 0
    
    def get_all_sync_status(self):
        """获取所有同步状态"""
        try:
            self.cursor.execute('SELECT * FROM sync_status ORDER BY updated_at DESC')
            return [dict(row) for row in self.cursor.fetchall()]
        except:
            return []
    
    def save_contact(self, contact_data):
        """保存联系人信息"""
        try:
            self.cursor.execute('''
                INSERT INTO contacts (username, nick_name, remark, avatar)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    nick_name = excluded.nick_name,
                    remark = excluded.remark,
                    avatar = excluded.avatar,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                contact_data.get('username', ''),
                contact_data.get('nick_name', ''),
                contact_data.get('remark', ''),
                contact_data.get('avatar', '')
            ))
            self.conn.commit()
        except Exception as e:
            print(f"[!] 保存联系人失败: {e}")
    
    def get_contact_name(self, username):
        """获取联系人显示名称"""
        try:
            self.cursor.execute(
                'SELECT remark, nick_name FROM contacts WHERE username = ?',
                (username,)
            )
            row = self.cursor.fetchone()
            if row:
                return row['remark'] or row['nick_name'] or username
            return username
        except:
            return username
    
    def get_stats(self):
        """获取数据库统计信息"""
        try:
            stats = {}
            
            # 消息总数
            self.cursor.execute('SELECT COUNT(*) as count FROM messages')
            stats['total_messages'] = self.cursor.fetchone()['count']
            
            # 今日消息数
            today = datetime.now().strftime('%Y-%m-%d')
            self.cursor.execute(
                "SELECT COUNT(*) as count FROM messages WHERE create_time_str LIKE ?",
                (f'{today}%',)
            )
            stats['today_messages'] = self.cursor.fetchone()['count']
            
            # 联系人数量
            self.cursor.execute('SELECT COUNT(*) as count FROM contacts')
            stats['total_contacts'] = self.cursor.fetchone()['count']
            
            # 聊天数量
            self.cursor.execute('SELECT COUNT(DISTINCT username) as count FROM messages')
            stats['total_chats'] = self.cursor.fetchone()['count']
            
            # 最后同步时间
            self.cursor.execute(
                'SELECT MAX(updated_at) as last_sync FROM sync_status'
            )
            row = self.cursor.fetchone()
            stats['last_sync'] = row['last_sync'] if row and row['last_sync'] else '从未'
            
            return stats
        except Exception as e:
            print(f"[!] 获取统计信息失败: {e}")
            return {}
    
    def search_messages(self, keyword, limit=100):
        """搜索消息"""
        try:
            self.cursor.execute('''
                SELECT * FROM messages 
                WHERE content LIKE ? 
                ORDER BY create_time DESC 
                LIMIT ?
            ''', (f'%{keyword}%', limit))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"[!] 搜索消息失败: {e}")
            return []
    
    def get_recent_messages(self, username=None, limit=50):
        """获取最近消息"""
        try:
            if username:
                self.cursor.execute('''
                    SELECT * FROM messages 
                    WHERE username = ?
                    ORDER BY create_time DESC 
                    LIMIT ?
                ''', (username, limit))
            else:
                self.cursor.execute('''
                    SELECT * FROM messages 
                    ORDER BY create_time DESC 
                    LIMIT ?
                ''', (limit,))
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"[!] 获取最近消息失败: {e}")
            return []
    
    def set_config(self, key, value):
        """设置配置项"""
        try:
            self.cursor.execute('''
                INSERT INTO config (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            ''', (key, str(value)))
            self.conn.commit()
        except Exception as e:
            print(f"[!] 保存配置失败: {e}")
    
    def get_config(self, key, default=None):
        """获取配置项"""
        try:
            self.cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
            row = self.cursor.fetchone()
            return row['value'] if row else default
        except:
            return default
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
