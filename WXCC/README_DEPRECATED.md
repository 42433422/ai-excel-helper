# WXCC — 已废弃

本目录为早期微信小程序示例栈（含 mock 登录），**不再作为 XCAGI 正式客户端**。

## 正式小程序

请使用 [`FHD/XCAGI/miniprogram`](../XCAGI/miniprogram) 与后端：

- `POST /api/mp/v1/auth/login` → [`app/services/wechat_miniprogram_auth.py`](../app/services/wechat_miniprogram_auth.py)

## 请勿

- 在新功能中引用 `WXCC/utils/request.js` 的 mock 模式
- 与 Android / FHD Electron 并行维护第三套登录 UI
