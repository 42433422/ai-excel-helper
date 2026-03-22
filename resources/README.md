# XCAGI resources

此目录用于存放 **运行期需要但不属于业务代码的资源**，保证 XCAGI 运行时不依赖项目外部路径。

建议子目录：

- `config/`：可选配置文件（如 `deepseek_config.py`）
- `ai_assistant/`：旧版 AI 助手迁移过来的上传模板/生成模板等资源（例如 `uploads/`）
- `wechat-decrypt/`：微信解密后的 message db（如 `decrypted/message/message_0.db`）
- `wechat_cv/`：微信相关工具代码（如 `wechat_db_read.py`、`wechat_cv_send.py` 等）

如果你要进行“外部文件大清理”，请先把需要的文件搬到这里，再确认服务正常运行。

