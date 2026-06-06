# 离线版停发 — 站外操作清单（人工）

桌面与 Android 代码已改为 **personal + enterprise** 双 SKU。发版时请在站外完成：

## update.xcagi.com

- 新包仅上传到 `/releases/stable/personal/` 与 `/releases/stable/enterprise/`
- **不再**向 `/releases/stable/offline/` 上传新版本（历史目录可只读保留）

## MODstore 官网下载页

在 `MODstore_deploy`（或实际 market 前端仓库）：

1. 下载卡片由三张改为两张：**个人版**、**企业版**
2. 移除「离线版」标题与 `XCAGI-Offline-Setup-*.exe` 链接
3. 环境变量仍为：

```env
VITE_XCAGI_DOWNLOAD_VERSION=8.0.0
VITE_XCAGI_DOWNLOAD_BASE_URL=https://update.xcagi.com/releases/stable
```

4. 重建并部署 market 前端

## Android 分发

- 对外提供 `app-personal-*.apk` 与 `app-enterprise-*.apk`（或对应 release 签名包）
- 应用商店若曾上架单一 `com.xiuci.xcagi.mobile`，需改为两个 applicationId 分别上架或迁移说明
