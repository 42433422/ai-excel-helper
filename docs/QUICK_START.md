# XCAGI v8.0 快速开始（可交付宿主）

> 约 5 分钟跑通：**独立宿主 + 装 MOD 变系统**。主入口 `XCAGI/run.py` → `http://127.0.0.1:5000`

---

## 产品模型（1 分钟理解）

1. 你拿到的是 **XCAGI 宿主**（空壳 + 通用能力），不是某一家客户的成品 ERP。
2. 从 **扩展市场** 安装平台 MOD 后，这一份软件才变成「出货系统 / 涂料 ERP / …」。
3. 数据在**客户自己的机器**上，不由供应商代管。

---

## 前置条件

- **Python** 3.11+
- **Node.js** 18+（仅前端开发或重编 UI 时需要）
- **操作系统**：Windows 10/11、Linux macOS

---

## 方式 A：桌面安装包（推荐客户）

1. 运行供应商提供的 **XCAGI Setup 8.0.0**（generic 壳）。
2. 首次启动：若提示装 Mod 包，在 **扩展市场** 点 **一键装齐通用包**。
3. 验证：浏览器或壳内打开 → **智能对话** 可用；`GET http://127.0.0.1:5000/api/platform-shell/deliverable-status` 中 `"deliverable": true`。

详见 [customer/CUSTOMER_SUPPORT.md](customer/CUSTOMER_SUPPORT.md)。

---

## 方式 B：源码 / 开发机

### 1. 克隆与依赖

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 启动（按场景选择）

**桌面交付验收（SQLite，无需 Docker/PostgreSQL）：**

```bat
start-desktop-sqlite.bat
```

或 `start-dev.bat`（默认同样走 `xcagi-backend-desktop.cmd`）。

**Web / PostgreSQL 开发：**

```bash
alembic upgrade head   # 首次需迁移
cd XCAGI
start-xcagi.bat        # 或 xcagi-backend.cmd，读取 .env 中的 DATABASE_URL
```

桌面模式默认 SQLite，可跳过 `alembic` 与 PostgreSQL。详见 [guides/DESKTOP_DATABASE_DELIVERY.md](guides/DESKTOP_DATABASE_DELIVERY.md)。

### 3. 验证

- 桌面：`GET http://127.0.0.1:5000/api/desktop/status` → `storageMode: local_sqlite`
- 通用：打开 **http://127.0.0.1:5000/** ，API 文档 **/docs**

### 4. 前端（可选，开发）

```bash
cd frontend
npm install
npm run dev
```

默认构建为 **generic 壳**：`npm run build`；完整 ERP 侧栏：`npm run build:full`。

---

## 首次使用流程（界面）

generic 构建首次打开会进入 **首次设置**（`/onboarding`）：

1. 认识宿主 → 2. 宿主包就绪（一键装齐）→ 3. 行业定型（可跳过）→ 4. 智能对话  

详见 **[guides/PRODUCT_USER_FLOW.md](guides/PRODUCT_USER_FLOW.md)**。

## 装齐通用 Mod 包（命令行）

```bash
curl -X POST "http://127.0.0.1:5000/api/mod-store/bootstrap-edition-pack?edition=generic"
```

或在 UI：**首次设置** / **扩展市场** → **一键装齐通用包**。

---

## 发版 / 验收（供应商）

```powershell
powershell -File scripts/dev/adcdfg_acceptance.ps1
powershell -File scripts/dev/deliverable_smoke.ps1
powershell -File scripts/package/build-all-skus.ps1 -Version 8.0.0
```

完整清单：[DELIVERABLE_PRODUCT.md](DELIVERABLE_PRODUCT.md)

---

## 相关文档

- [DELIVERABLE_PRODUCT.md](DELIVERABLE_PRODUCT.md) — 交付物与验收
- [guides/PLATFORM_SHELL.md](guides/PLATFORM_SHELL.md) — 宿主壳与 edition
- [guides/ADCDFG_COMPLETION_PLAN.md](guides/ADCDFG_COMPLETION_PLAN.md) — 收口计划
- [ARCHITECTURE.md](ARCHITECTURE.md) — 架构
