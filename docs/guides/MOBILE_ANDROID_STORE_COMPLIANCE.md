# XCAGI Android 应用商店合规清单

## 分发包

| SKU | applicationId | 目录 |
|-----|---------------|------|
| 个人版 | `com.xiuci.xcagi.mobile.personal` | `release/packages-v*/personal/`、`个人版/` |
| 企业版 | `com.xiuci.xcagi.mobile.enterprise` | `release/packages-v*/enterprise/`、`企业版/` |

## 隐私与协议

- 首次启动展示隐私同意页，版本号由 `GET /api/app/config` 的 `legal_version` 控制。
- 默认链接：`https://xiu-ci.com/legal/privacy`、`https://xiu-ci.com/legal/terms`。
- 账号注销：`POST /api/auth/account/delete`（需密码）。

## 权限说明

| 权限 | 用途 |
|------|------|
| INTERNET | 云端工作台、登录、对话 |
| ACCESS_NETWORK_STATE | 离线提示 |
| CAMERA | 扫描电脑配对二维码 |
| POST_NOTIFICATIONS | 审批/系统通知（Android 13+） |

## 推送（国内商店）

1. **Firebase**：在 Firebase 控制台创建项目，添加 personal/enterprise 两个 Android 应用，将 `google-services.json` 放入 `app/src/personal/`、`app/src/enterprise/`。
2. **极光 JPush**：在 [极光控制台](https://www.jiguang.cn/) 创建应用，在 `local.properties` 设置 `JPUSH_APPKEY=你的AppKey`。
3. 服务端 FHD：配置 `FIREBASE_SERVICE_ACCOUNT_JSON`、`JPUSH_APP_KEY`、`JPUSH_MASTER_SECRET` 后审批事件可推送。

## App Links

部署 `https://xiu-ci.com/.well-known/assetlinks.json`（模板见 `FHD/docs/guides/assetlinks.json.example`），包名与 release 签名 SHA256 需与商店证书一致。

## 版本策略

`GET /api/app/config` 字段：

- `min_android_version`：低于此 versionCode 强制更新
- `latest_android_version`：可选更新提示
- `apk_download_url`：对应 SKU 的 APK 下载地址

环境变量（MODstore）：`XCAGI_ANDROID_MIN_VERSION_CODE`、`XCAGI_ANDROID_LATEST_VERSION_CODE`、`XCAGI_ANDROID_LATEST_VERSION_NAME`。

## 真机验收（1.4.0）

1. 首次安装 → 隐私同意 → 登录 → 首页/对话/工作台
2. 个人账号仅个人包可登录；企业账号仅企业包
3. 检查更新、注销账号
4. 审批推送（企业版 + 服务端密钥已配置）
5. 扫码配对电脑（可选）
