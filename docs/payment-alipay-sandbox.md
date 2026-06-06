# 支付宝「模型支付」沙箱跑通清单

本页只讲一件事：在本机把「模型支付」页跑到 **扫码付款 → 异步通知 → 标记 paid → 前端出现「已购 ×N」**。

涉及代码：

- `app/fastapi_routes/model_payment.py`(路由)
- `app/infrastructure/payment/alipay.py`(支付宝 SDK 封装)
- `app/infrastructure/payment/order_store.py`(订单持久化)
- `scripts/backend-legacy/scripts/test_alipay_sandbox.py`(沙箱验证脚本,历史归档)
- `frontend/src/views/ModelPaymentView.vue`

## 0. 准备

1. 在 [支付宝开放平台](https://open.alipay.com/) 创建/进入 **沙箱应用**（或正式应用的沙箱版本）。
2. 用 **密钥工具** 生成 **RSA2** 密钥对，**应用公钥** 粘到沙箱应用里保存。
3. 记录以下三项（**不要**贴到仓库或聊天）：
   - 沙箱 `APPID`
   - 应用私钥 PEM
   - 平台上展示的「支付宝公钥」

仓库里默认读取 `424/alipayPublicKey_RSA2.txt` 作为「支付宝公钥」；**如果你已替换为正确内容**，无需额外配置；否则优先用环境变量覆盖。

## 1. 配置 .env

在仓库根 `.env`（或 `XCAGI/.env`，任一处，不要提交到 Git）写入：

```bash
ALIPAY_APP_ID=沙箱APPID
# 私钥整段一行，换行写成字面量 \n
ALIPAY_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
# 或改用文件路径（验完删文件、改用环境变量更安全）
# ALIPAY_APP_PRIVATE_KEY_PATH=E:/keys/alipay_app_private.pem

# 覆盖仓库内默认公钥（可选）
# ALIPAY_ALIPAY_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----

# 沙箱开关
ALIPAY_DEBUG=1

# 公网异步通知地址，与开放平台里一致
ALIPAY_NOTIFY_URL=https://your-tunnel.example.com/api/model-payment/notify/alipay
```

## 2. 安装依赖并重启

```bash
cd XCAGI
pip install -r requirements.txt
# 重启 FastAPI（本地 run_fastapi / uvicorn / 你的启动脚本）
```

## 3. 本机自测（不走网络服务器）

```bash
# 只看诊断（配置来源、notify path 是否对齐）
python -m backend.scripts.test_alipay_sandbox

# 发一笔 0.01 元沙箱预下单，成功会打印 qr_code
python -m backend.scripts.test_alipay_sandbox --precreate
```

- `alipay_configured: true` + `sdk_installed: true` = 已就绪。
- `notify_url_path_ok: false` 表示 `ALIPAY_NOTIFY_URL` 的路径不对，应为 `/api/model-payment/notify/alipay`。
- `--precreate` 的 `qr_code` 可用任意二维码工具/App 扫描，沙箱买家付款。

## 4. 前端跑一次

> **注意（2026-05）**：`模型支付` 前端页面已改为外链模式，点击后跳转修茈市场套餐/钱包页，**不再在本机生成扫码订单**。
> 若需测试本机下单闭环，请直接调后端接口（见步骤 2）或通过 `curl` 验证。

1. 浏览器打开 `模型支付` 页，确认「套餐/钱包」外链能正常打开。
2. 后端接口验证（替代前端二维码测试）：

```bash
# 下单（需先在 .env 配置 ALIPAY_DEBUG=true 与正确密钥）
curl -X POST http://127.0.0.1:5000/api/model-payment/checkout \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"basic","buyer_id":"test_user"}'

# 查看权益
curl http://127.0.0.1:5000/api/model-payment/entitlements
```

付款成功后约数秒内，`/api/model-payment/entitlements` 返回有效权益记录。

也可直接调接口核对：

```bash
curl http://127.0.0.1:5000/api/model-payment/diagnostics
curl http://127.0.0.1:5000/api/model-payment/entitlements
```

## 5. 公网异步通知

开放平台的异步通知 **必须**能访问到你这台机。本地开发任选其一：

- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)：`cloudflared tunnel --url http://127.0.0.1:5000`
- [ngrok](https://ngrok.com/)：`ngrok http 5000`

三处必须 **完全一致**：

1. 开放平台里应用的「异步通知地址」
2. `.env` 里的 `ALIPAY_NOTIFY_URL`
3. 实际转发到后端的 URL（path 必须是 `/api/model-payment/notify/alipay`）

若通知一直收不到：

- 先看 `diagnostics` 中的 `notify_url_path_ok`；
- 再看 FastAPI 日志有没有 `alipay notify` 的 warning / error。

## 6. 订单与权益数据

所有订单与权益都落在本地 JSON：

```
data/model_payment_orders.json
```

结构：

```json
{
  "orders": {
    "mp-xxx": { "status": "paid", "trade_no": "...", "notify_count": 1 }
  },
  "entitlements": {
    "demo-pro": { "plan_id": "demo-pro", "purchase_count": 1, "last_paid_at": "..." }
  }
}
```

幂等规则：支付宝重复发同一单通知时只累加 `notify_count`，`purchase_count` 仅在 **首次** `marked_paid` 时 +1。

## 7. 切换正式

1. 去掉 `ALIPAY_DEBUG=1`；
2. 换成正式 `ALIPAY_APP_ID`、正式私钥、正式「支付宝公钥」；
3. 换成生产域名下的 `ALIPAY_NOTIFY_URL`，在开放平台里同步修改；
4. 再跑一次 `diagnostics` 确认 `debug_mode: false` 且 `alipay_configured: true`。

## 8. 安全红线（务必遵守）

- **应用私钥**只放在服务器（环境变量或密钥管理），**不要**出现在代码、日志、Git、聊天、截图里。
- `.gitignore` 已忽略 `**/alipay_*_private*.pem` 与 `data/model_payment_orders.json`。
- 前端同步返回不可信；**永远**以异步通知或主动查单结果为准。

## 9. 不在本接入范围内

- 主动查单 `alipay.trade.query` 与超时关单（目前只有 notify 一条路径）。
- 多用户账户体系：当前权益按 `plan_id` 聚合，不区分买家。
- 数据库持久化：需要写 `DATABASE_URL` 迁移时单独规划。
