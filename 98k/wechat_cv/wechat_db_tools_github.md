# GitHub 微信 PC dbkey / 数据库解密 相关项目参考

按类别整理的仓库，便于直接匹配「微信 PC 端 dbkey 提取」「聊天记录解密」「SQLCipher」「逆向提取 dbkey」等需求。仅供学习与研究，请遵守法律法规。

---

## 一、WeChat PC dbkey 直接提取

| 项目 | 链接 | 说明 |
|------|------|------|
| **WeChatDBKey** | https://github.com/git-jiadong/WeChatDBKey | Go 实现，获取微信数据库密钥，Apache-2.0 |
| **GetWeChatDBPassword** | https://github.com/L-HeliantHuS/GetWeChatDBPassword | Python，专门获取 Windows 版微信聊天库密码 |
| **wechat-decrypt** | https://github.com/ylytdeng/wechat-decrypt | Python，4.x 多平台，内存提 key + 解密 + Web 监听（本仓库已克隆在 `e:\FHD\wechat-decrypt`） |
| **Get-WeChat-DB** | https://github.com/A2kaid/Get-WeChat-DB | 获取目标机微信库与密钥，Client+Server，作者注明有 bug 需完善 |

---

## 二、WeChat Msg 数据库解密（聊天记录）

| 项目 | 链接 | 说明 |
|------|------|------|
| **wechat-decrypt** | https://github.com/ylytdeng/wechat-decrypt | 提 key + 批量解密 + 实时消息监听，支持 4.x |
| **decrypt-PC-WeChat-db** | https://github.com/zhimian/decrypt-PC-WeChat-db | 自动解密 PC 微信数据库，含 crypto 模块 |
| **wechat-db-decrypt** | https://github.com/qwe305/wechat-db-decrypt | Java，PC 端解密，支持到约 3.7.5.23，集成获取密钥 |
| **WeChatDB** | https://github.com/lich0821/WeChatDB | 已停止维护 |
| **EnMicroMsg** | https://github.com/84583728/EnMicroMsg | 解密 EnMicroMsg.db（偏安卓端） |
| **wechat-db** | https://github.com/listenzcc/wechat-db | 解析聊天记录与 db，对 3.x 支持较好，4.x 可能失败 |

---

## 三、SQLCipher + 微信解密

| 项目 | 链接 | 说明 |
|------|------|------|
| **wechat-decrypt** | https://github.com/ylytdeng/wechat-decrypt | 针对 SQLCipher 4（AES-256-CBC + HMAC-SHA512），内存 x'64hex+32salt' 匹配 + HMAC 校验 |
| **wechat-dump-rs** | https://github.com/0xlane/wechat-dump-rs | Rust，从运行中微信导出 key，自动解密所有库，支持导出 key 后离线解密 |
| **wdecipher** | https://github.com/gndlwch2w/wdecipher | Python，第三方扩展：取 db_key、找库位置、批量解密与合并、包级接口 |

---

## 四、微信逆向 / 逆向提取 dbkey

| 项目 | 链接 | 说明 |
|------|------|------|
| **wechat-dump-rs** | https://github.com/0xlane/wechat-dump-rs | Rust，从进程导出 key + 解密，偏工程化 |
| **WeChat-ReverseCode** | https://github.com/xqc016123/WeChat-ReverseCode | 逆向头文件/源码与逆向工具 |
| **WeChatDBKey** | https://github.com/git-jiadong/WeChatDBKey | Go，直接获取 dbkey |
| **wechat-db** | https://github.com/listenzcc/wechat-db | 含提 key、解密脚本，3.x 更稳 |

---

## 使用与注意

- **本仓库**（wechat_cv / wechat_db_read）：只读「已解密」库或「用 wechat_db_key.json 配置的 key_hex」解密；不实现从内存提 key，可与上述工具配合（用它们提 key → 写入配置 → 本仓库读库）。
- **0/17 或候选无效**：可尝试以管理员运行 wechat-decrypt；或换用 WeChatDBKey、wechat-dump-rs、GetWeChatDBPassword 等看是否适配当前微信版本。
- 新版本若采用盐值动态/加密或 dbkey 二次加密，上述项目也可能需等更新才能提 key。

上述链接均为 GitHub 公开仓库，可直接在 GitHub 搜索仓库名进入。
