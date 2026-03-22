# XCAGI v3.0.0 发布信息

> 发布日期：2026-03-23  
> 版本：3.0.0  
> 状态：✅ 已发布

---

## 📦 版本信息

| 组件 | 版本 |
|------|------|
| **后端** | 3.0.0 |
| **前端** | 3.0.0 |
| **数据库架构** | 3.0.0 |
| **API 版本** | v3 |

---

## 🎯 重大更新

### 核心功能

1. **混合意图识别引擎** ⭐⭐⭐
   - 规则系统 + RASA NLU + BERT 三重保障
   - 意图识别准确率 98%+
   - 离线可用（蒸馏模型）

2. **TTS 语音合成** ⭐⭐⭐
   - Edge TTS 集成
   - 多音色、语速/音调可调
   - 智能语音播报

3. **任务自动化 Agent** ⭐⭐⭐
   - 智能任务代理
   - 自动执行复杂流程
   - 异步任务队列

4. **微信生态集成** ⭐⭐
   - 消息自动处理
   - 联系人同步
   - 消息解密

5. **DDD 领域驱动设计** ⭐⭐
   - 领域层、应用层、基础设施层
   - 仓储模式
   - 领域实体和值对象

6. **数据库迁移系统** ⭐⭐
   - Alembic 版本管理
   - 自动迁移
   - 回滚支持

### 技术栈升级

| 组件 | v2.0 | v3.0 |
|------|------|------|
| Flask | 2.0+ | 3.0+ |
| SQLAlchemy | 基础 | 2.0+ |
| 数据库迁移 | 手动 | Alembic |
| 前端状态管理 | - | Pinia 3.0+ |
| 构建工具 | 基础 | Vite 4.4+ |
| 意图识别 | 云端 API | 混合离线 |
| 架构模式 | 简单分层 | DDD |

---

## 📊 性能提升

| 指标 | v2.0 | v3.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~3s | ~1.5s | ⬆️ **50%** |
| 意图识别准确率 | ~85% | ~98% | ⬆️ **13%** |
| 响应速度 | 基础 | 优化 | ⬆️ **显著提升** |
| 离线可用性 | ❌ | ✅ | ⬆️ **完全支持** |
| 架构模式 | MVC | DDD | ⬆️ **可维护性** |

---

## 📝 安装说明

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/42433422/xcagi.git
cd xcagi

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动服务
python run.py
```

访问：http://localhost:5000

### Docker 安装

```bash
# 使用 Docker Compose
docker-compose up -d
```

---

## 📚 文档

- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 🛠️ [部署指南](docs/DEPLOYMENT.md)
- 📝 [更新日志](CHANGELOG.md)
- 🔒 [安全策略](SECURITY.md)
- 🤝 [贡献指南](.github/CONTRIBUTING.md)

---

## ⚠️ 破坏性变更

### 数据库迁移

v3.0.0 引入了新的数据库架构，需要运行迁移：

```bash
# 运行数据库迁移
alembic upgrade head
```

### 配置文件调整

- 环境变量文件位置：`resources/config/.env.example`
- 新增配置项：`USE_LOCAL_BERT`, `TTS_VOICE` 等

### API 端点调整

部分 API 端点有调整，请参考：
- [API 文档](http://localhost:5000/apidocs)
- [迁移指南](docs/migration_guide.md)

---

## 🙏 致谢

感谢所有贡献者和用户的支持！

特别感谢以下开源项目：
- Vue.js
- Flask
- SQLAlchemy
- DeepSeek AI
- RASA
- Hugging Face Transformers

---

## 📬 联系方式

- **GitHub**: https://github.com/42433422/xcagi
- **Issues**: https://github.com/42433422/xcagi/issues
- **Discussions**: https://github.com/42433422/xcagi/discussions

---

## 📄 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

---

*发布日期：2026-03-23*  
*版本：3.0.0*  
*状态：✅ 已发布*
