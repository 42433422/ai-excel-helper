# XCAGI 双 SKU 发版指南（8.0+）

## 1. 发版前安全自检

```powershell
cd e:\XCMAX\FHD
powershell -ExecutionPolicy Bypass -File scripts/package/pre-release-security.ps1 -Phase pre -Version 8.0.0
```

## 2. 构建两个安装包

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package/build-all-skus.ps1 -Version 8.0.0
```

可选：构建时为 `latest.yml` 增加 Ed25519 签名：

```powershell
$env:XCAGI_UPDATE_ED25519_PRIVATE_KEY = "<PEM 私钥，勿提交 git>"
```

## 3. 构建后验收

```powershell
$v = "8.0.0"
foreach ($sku in @("personal","enterprise")) {
  powershell -File scripts/package/verify-bundled-mods.ps1 -ProductSku $sku `
    -UnpackedDir "release/xcagi-v$v/$sku/win-unpacked/resources/backend/_internal/mods"
}
powershell -File scripts/package/pre-release-security.ps1 -Phase post -Version $v
```

## 4. 上传到 update.xcagi.com（rsync）

设置环境变量（当前 PowerShell 会话或 CI secret）：

| 变量 | 示例 |
|------|------|
| `XCAGI_UPDATE_SSH_HOST` | `update.xcagi.com` 或服务器 IP |
| `XCAGI_UPDATE_SSH_USER` | `deploy` |
| `XCAGI_UPDATE_SSH_PATH` | `/var/www/update/releases/stable` |
| `XCAGI_UPDATE_SSH_KEY` | `C:\Users\you\.ssh\id_ed25519` |

```powershell
powershell -File scripts/package/upload-release-skus.ps1 -Version 8.0.0
# 试跑: -DryRun
```

远端目录结构：

```
/releases/stable/personal/XCAGI-Personal-Setup-8.0.0-x64.exe
/releases/stable/personal/latest.yml
/releases/stable/enterprise/...
```

**勿上传**无 `-ProductSku` 的 legacy `XCAGI-Setup-*.exe` 到 `personal/`，以免 ERP 源码重新暴露。

## 5. MODstore 官网下载

在服务器 `MODstore_deploy/.env.production`：

```env
VITE_XCAGI_DOWNLOAD_VERSION=8.0.0
VITE_XCAGI_DOWNLOAD_BASE_URL=https://update.xcagi.com/releases/stable
```

重建并部署 market 前端后，下载页两卡（个人版 / 企业版）指向上述 URL。

## 6. 发版后抽检

- 两个 URL 可 HTTP 下载，体积合理
- 安装 personal：无法启用 ERP Mod
- 安装 enterprise：ERP 菜单可用
- 各 SKU 自动更新仅拉各自 `latest.yml`

## 7. Android 双 App

```bat
cd mobile-android
gradlew.bat assemblePersonalDebug assembleEnterpriseDebug
```

个人版与企业版可同时安装（不同 `applicationId`）。

## 8. 本地分发目录（Windows + Android 放一起）

```powershell
powershell -File scripts/package/stage-sku-download-folders.ps1 -Version 8.0.0
```

产出：`release/packages-v8.0.0/` 下两个文件夹，各含 **1 个 Windows exe + 1 个 Android apk**：

| 文件夹 | Windows | Android |
|--------|---------|---------|
| `personal`（可重命名为 `个人版`） | `XCAGI-Personal-Windows-{ver}-x64.exe` | `XCAGI-Personal-Android-{ver}.apk` |
| `enterprise`（可重命名为 `企业版`） | `XCAGI-Enterprise-Windows-{ver}-x64.exe` | `XCAGI-Enterprise-Android-{ver}.apk` |
