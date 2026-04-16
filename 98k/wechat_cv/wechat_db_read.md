# 用 SQL 读微信本地数据库

## 能不能用 SQL 读？

**能，但有个前提：微信 PC 版的聊天库是加密的，要先解密才能用 SQL 查。**

- 聊天记录、联系人等存在本地 **SQLite 数据库**里（如 `Msg\MSG0.db`、`MicroMsg.db` 等）。
- 从较新版本起，这些库用 **SQLCipher** 加密（AES-256），直接用 `sqlite3.open("xxx.db")` 会报错或乱码。
- 解密需要**密钥**，密钥在**微信进程内存**里；通常要借助第三方工具在微信运行时从进程里提出密钥，再解密成普通 SQLite 文件。

所以：**“用 SQL 获取微信信息” = 先解密 → 得到普通 .db 文件 → 再用 SQL 查询。**

---

## 数据大概在哪？

- 默认：`%USERPROFILE%\Documents\WeChat Files\<你的微信ID>\`
- 也可能在：微信 **设置 → 文件管理** 里看到的“文件管理”目录。
- 下面常见有：
  - `Msg\MSG0.db`, `MSG1.db`, ...：聊天消息（按账号/时间分库）
  - `MicroMsg.db`：账号、联系人等
  - 其它 .db：配置、媒体索引等

具体表名因版本会略有差异（如 `MSG`、`Contact` 等），需用 DB 工具打开解密后的库看一下。

---

## 推荐做法（解密后再用 SQL）

1. **解密**（任选其一）：
   - [wechat-db-decrypt](https://github.com/zzyzhangziyu/wechat-db-decrypt)（需微信运行，从进程取密钥后解密）
   - [wechat-decrypt (ylytdeng)](https://github.com/ylytdeng/wechat-decrypt)（Python，支持解密 + 导出）
   - 其它你信任的“微信聊天记录导出/解密”工具，导出为 **未加密的 .db 或 SQLite 文件**。

2. **用 SQL 读**：
   - 解密后会得到可正常打开的 .db 文件。
   - 用本目录下的 `wechat_db_read.py`（见下方）指定该文件路径，即可用 SQL 查询联系人、最近聊天等（需根据实际表结构改表名/字段名）。

**注意**：从进程内存取密钥通常需要管理员权限，且仅限在你自己电脑、自己的微信数据上做备份/导出，请遵守相关法律和微信使用条款。

---

## 微信 PC 4.x+ 的 dbkey 从哪里来？

微信 PC 版（4.x+）的本地库（如 Msg.db、MicroMsg.db、db_storage 下的 .db）采用 **SQLCipher** 加密，解密所需的是 **dbkey**（64 位 Hex 密钥）。该密钥在微信启动后被加载到 **进程内存** 中，获取思路是：

1. **定位微信 PC 进程**：找到 `WeChat.exe` 及其进程 ID（PID）。
2. **扫描进程内存**：对 WeChat 进程的可读内存区域进行扫描，查找符合 dbkey 特征的数据（例如连续 64 位十六进制字符、或与 SQLCipher 使用方式相关的内存布局）。
3. **提取并解析**：从命中区域中解析出 **64 位 Hex** 格式的密钥，写入本地的 `wechat_db_key.json` 的 `key_hex` 字段，供 `wechat_db_read.py` 使用。

实现时通常需要：Windows API（`OpenProcess`、`ReadProcessMemory`、`VirtualQueryEx` 等）或封装库、适当进程权限（常需管理员）、以及 dbkey 在内存中的特征或偏移。

- **dbkey 核心特征**：**64 个十六进制字符**（32 字节），即纯 `[0-9a-f]` 的 64 位字符串；SQLCipher 使用的就是该 32 字节密钥。
- **按偏移取 key**：[GetWeChatDBPassword](https://github.com/L-HeliantHuS/GetWeChatDBPassword) 通过 Pymem 读 **WeChatWin.dll 基址 + 版本偏移** 处指针，再读 32 字节即得 64 位 hex；需 WeChat.exe + WeChatWin.dll，若仅有 WeChatAppEx.exe 可能无此 DLL，需以管理员运行或改用内存扫描。
- **内存扫描**：wechat-decrypt、本目录 `wechat_db_key_from_memory.py` 等通过扫描进程内存中的 64/96 位 hex 并用 HMAC 或 SQLCipher 验证。

本仓库不内置从内存提取 key 的完整实现，仅支持「从配置文件读取已获取的 key_hex」并解密库。

### 新版本可能的变化（导致 0/17 或扫不到 key）

部分**较新微信 PC 版本**可能对密钥/盐值做了加固，内存扫描会失效或长期 0/17，例如：

- **盐值动态生成 / 加密存储**：salt 不再以明文 32 位 hex 与 enc_key 连续存放在内存，或 salt 本身被加密，无法用「DB 文件头 16 字节 salt + HMAC」直接匹配。
- **dbkey 二次加密**：原始 64/96 位 key 在写入进程内存前被再次加密（如 AES-128），内存中看到的是密文或中间形式，直接按 `x'<64hex><32hex>'` 或 64/96 位 hex 匹配无法得到可用密钥。

若你确认当前为上述新版本行为，可：

1. **以管理员权限**多试几次 wechat-decrypt / 本仓库的进程扫描（有时不同时刻内存布局不同）。
2. 关注 wechat-decrypt、GetWeChatDBPassword 等项目的 **Issue/更新**，看是否有针对新版本的逆向与适配。
3. 若已有**旧版微信**导出的解密库或 key，可继续用本仓库的 `wechat_db_read.py` + `wechat_db_key.json` 读库。

---

## 候选密钥验证（SQLCipher）

获取候选密钥（如从进程内存扫描）后，可用本仓库提供的接口验证是否有效：

- **函数**：`wechat_db_read.verify_wechat_db_key(key_hex, db_path)`  
  返回 `{"valid": True/False, "message": "..."}`。
- **命令行**：`python wechat_db_verify_key.py <64或96位Hex> <db路径>`。

**注意**：必须使用 **sqlcipher3** 或 **pysqlcipher3** 才能解密；**标准库 `sqlite3` 无法解密 SQLCipher 加密库**（执行 `PRAGMA key` 后仍会报错或乱码）。正确做法是用本模块的 `verify_wechat_db_key` 或 `_connect_encrypted`（内部优先使用 sqlcipher3，其次 pysqlcipher3）。

**安装**（二选一即可）：
- **Windows 推荐**：`pip install sqlcipher3`（有预编译 wheel，无需编译）
- Linux/macOS 或需从源码编译时：`pip install pysqlcipher3`（需系统先安装 libsqlcipher-dev）

```python
# 正确方式（需 pip install pysqlcipher3）
from wechat_db_read import verify_wechat_db_key

key_hex_64 = "你的候选64位Hex密钥"
db_path = r"微信数据库路径\message_0.db"

result = verify_wechat_db_key(key_hex_64, db_path)
print("密钥有效" if result["valid"] else result["message"])
```

---

## 本仓库里的“读库”支持

- `wechat_cv_send.py`：**不读数据库**，只用截屏 + OCR 获取当前聊天和对方消息（无需解密）。
- `wechat_db_read.py`：支持**已解密**或**用 wechat_db_key.json 配置密钥解密**后读库；并提供**用本地 DB 替代 OCR** 的接口：
  - **联系人名 + 对方消息**：`get_contact_and_messages_from_db(contact_identifier, ...)` — 根据微信 ID/备注/昵称直接返回联系人名称和消息列表，无需打开微信窗口。
  - 辅助：`get_contact_list_from_db()`、`get_wechat_msg_db_paths()`、`get_wechat_contact_db_path()` 等。

若你已经有解密后的 .db 或已配置 key，可直接用 `wechat_db_read.py` 查；MCP 工具 `wechat_db_get_contact_messages` / `wechat_db_list_contacts` 会调用上述接口，优先用 DB 替代 CV 获取联系人名与聊天记录。

---

## 获取本地聊天的功能（统一入口）

| 方式 | 入口 | 条件 |
|------|------|------|
| **统一脚本** | `python get_local_chat.py [联系人名]` | 传联系人 → 从 DB 取；不传 → 从当前窗口 OCR |
| **仅列联系人** | `python get_local_chat.py --list` | 从 DB 列联系人，需已配置 key |
| **DB 接口** | `get_contact_and_messages_from_db("备注或昵称")` | 需 wechat_db_key.json；无需打开微信 |
| **当前窗口 OCR** | `get_current_chat_contact_name()` + `get_current_chat_messages()` | 需微信在前台且已打开某聊天 |
| **MCP 工具** | `wechat_db_get_contact_messages` / `wechat_db_list_contacts` | 同 DB 接口，供 Cursor/Claude 调用 |
| **完整流程 CV** | `python wechat_cv_full_flow.py 联系人名` | 搜索 → 进聊天 → 取联系人名 + 消息（OCR） |

推荐：已配置密钥时用 **get_local_chat.py** 或 **wechat_db_get_contact_messages** 从本地 DB 获取；未配置时用当前窗口 OCR 或 wechat_cv_full_flow。
