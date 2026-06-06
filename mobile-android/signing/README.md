# Android Release 签名

本目录用于存放 **正式 Release 密钥库**（`xcagi-release.jks`），文件已加入 `.gitignore`，请勿提交到 Git。

## 首次生成

在 `FHD` 目录执行：

```powershell
powershell -File scripts/package/new-android-release-keystore.ps1
```

按提示设置密码后，会在本目录生成 `xcagi-release.jks`，并在 `mobile-android/keystore.properties` 写入配置。

## 备份

请将 `.jks` 与密码存入公司密钥管理（密码管理器 / 离线保险柜）。丢失后无法为同一 `applicationId` 发布更新包。

## 构建已签名 Release

```powershell
powershell -File scripts/package/build-android-release-signed.ps1
```
