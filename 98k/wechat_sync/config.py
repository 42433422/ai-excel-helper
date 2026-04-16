"""
微信消息同步系统配置
"""
import os
import json
import platform

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "sync_config.json")

# 默认配置
DEFAULT_CONFIG = {
    # 微信数据目录 (会自动检测)
    "wechat_db_dir": "",
    
    # 解密密钥文件路径
    "keys_file": os.path.join(BASE_DIR, "all_keys.json"),
    
    # 解密后的数据库输出目录
    "decrypted_dir": os.path.join(BASE_DIR, "decrypted"),
    
    # 本地同步数据库路径
    "local_db_path": os.path.join(BASE_DIR, "wechat_messages.db"),
    
    # 轮询间隔 (毫秒)
    "poll_interval_ms": 100,
    
    # 批量插入大小
    "batch_size": 100,
    
    # 日志级别
    "log_level": "INFO",
    
    # 微信进程名
    "wechat_process": "Weixin.exe" if platform.system() == "Windows" else "wechat",
    
    # 同步的消息类型 (1=文本, 3=图片, 34=语音, 43=视频, 47=表情, 49=链接/文件)
    "sync_msg_types": [1, 3, 34, 43, 47, 49],
    
    # 是否同步群聊消息
    "sync_group_messages": True,
    
    # 是否同步私聊消息
    "sync_private_messages": True,
    
    # 历史消息同步天数 (0=只同步新消息)
    "sync_history_days": 0,
}


def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置
            merged = DEFAULT_CONFIG.copy()
            merged.update(config)
            return merged
        except Exception as e:
            print(f"[!] 配置文件加载失败: {e}, 使用默认配置")
    
    # 创建默认配置文件
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[!] 配置文件保存失败: {e}")


def update_config(key, value):
    """更新配置项"""
    config = load_config()
    config[key] = value
    save_config(config)
