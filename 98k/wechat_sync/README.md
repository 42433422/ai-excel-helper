# 微信数据库解密与消息同步系统

基于开源工具 WeChatDB-Decrypt 的微信数据库解密和消息同步解决方案。

## 功能特性

- **一键密钥提取**: 从微信进程内存中自动提取 SQLCipher 数据库密钥
- **全库解密**: 解密所有微信本地数据库，输出标准 SQLite 格式
- **毫秒级轮询**: 100ms 间隔实时监听新消息
- **增量同步**: 只同步新消息，避免重复
- **本地存储**: 将消息同步到本地 SQLite 数据库
- **消息搜索**: 支持关键词搜索历史消息

## 系统要求

- Windows 10/11 或 Linux
- Python 3.10+
- 微信 4.x 版本
- 管理员权限 (用于读取进程内存)

## 快速开始

### 1. 安装依赖

```bash
cd wechat_sync
pip install -r requirements.txt
```

### 2. 自动设置

```bash
python main.py auto
```

### 3. 提取密钥

**需要以管理员身份运行**

```bash
python main.py extract
```

### 4. 启动消息同步

```bash
python main.py sync
```

## 详细使用说明

### 密钥提取

```bash
# 提取密钥 (需要管理员权限)
python main.py extract
```

密钥将保存到 `all_keys.json` 文件中。

### 数据库解密

```bash
# 解密所有数据库到 decrypted/ 目录
python main.py decrypt
```

### 消息同步

```bash
# 启动持续同步服务 (毫秒级轮询)
python main.py sync

# 执行一次同步
python main.py sync --once

# 查看同步统计
python main.py sync --stats

# 搜索消息
python main.py sync --search "关键词"

# 查看最近消息
python main.py sync --recent --limit 50
```

### 系统配置

```bash
# 交互式配置
python main.py config

# 设置特定配置项
python main.py config --key poll_interval_ms --value 200

# 重置配置
python main.py config --reset
```

## 配置文件

配置文件 `sync_config.json`:

```json
{
    "wechat_db_dir": "D:\\xwechat_files\\wxid_xxx\\db_storage",
    "keys_file": "all_keys.json",
    "decrypted_dir": "decrypted",
    "local_db_path": "wechat_messages.db",
    "poll_interval_ms": 100,
    "batch_size": 100,
    "sync_msg_types": [1, 3, 34, 43, 47, 49],
    "sync_group_messages": true,
    "sync_private_messages": true
}
```

## 本地数据库结构

同步的消息存储在 `wechat_messages.db` 中，包含以下表:

### messages 表
- `msg_id`: 消息唯一标识
- `username`: 聊天对象ID
- `chat_name`: 聊天对象名称
- `sender_id`: 发送者ID
- `sender_name`: 发送者名称
- `msg_type`: 消息类型 (1=文本, 3=图片, ...)
- `msg_type_name`: 消息类型名称
- `content`: 消息内容
- `create_time`: 创建时间戳
- `is_group`: 是否群聊

### contacts 表
- `username`: 微信ID
- `nick_name`: 昵称
- `remark`: 备注名

### sync_status 表
- `username`: 聊天对象
- `last_msg_time`: 最后同步时间
- `sync_count`: 同步消息数

## 技术原理

### 密钥提取
- 扫描微信进程内存
- 匹配 SQLCipher raw key 格式: `x'<64hex_key><32hex_salt>'`
- 通过 HMAC 验证密钥正确性

### 数据库解密
- 算法: AES-256-CBC + HMAC-SHA512
- KDF: PBKDF2-HMAC-SHA512, 256,000 iterations
- 页面大小: 4096 bytes

### 消息同步
- 监控 `session.db` 的变化
- 检测时间戳变化识别新消息
- 从 `message_N.db` 获取完整消息内容
- 批量写入本地数据库

## 项目结构

```
wechat_sync/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── key_extractor.py     # 密钥提取
├── db_decryptor.py      # 数据库解密
├── message_sync.py      # 消息同步
├── local_db.py          # 本地数据库管理
├── requirements.txt     # 依赖列表
└── README.md           # 说明文档
```

## 注意事项

1. **权限要求**: 密钥提取需要管理员/root权限
2. **微信运行**: 提取密钥时微信必须正在运行
3. **数据安全**: 密钥文件包含敏感信息，请妥善保管
4. **法律合规**: 仅用于解密自己的微信数据

## 依赖项目

本项目基于以下开源项目:
- [wechat-decrypt](https://github.com/nicoco007/wechat-decrypt) - 微信数据库解密
- [GetWeChatDBPassword](https://github.com/AdminTest0/GetWeChatDBPassword) - 密钥提取

## 许可证

仅供学习研究使用，请遵守相关法律法规。
