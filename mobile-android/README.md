# XCAGI Android

成都修茈科技有限公司 XCAGI 原生 Android 客户端（个人版 / 企业版双 SKU）。

- 技术栈：Kotlin、Jetpack Compose、Hilt、Retrofit、Room、WorkManager
- 完整说明：[docs/guides/MOBILE_ANDROID.md](../docs/guides/MOBILE_ANDROID.md)

## 快速开始

1. 云端：手机号登录 → 工作台 / 首页 MODstore 推荐
2. 局域网：PC 运行 FHD `python XCAGI/run.py --host 0.0.0.0 --port 5000` → 应用内连接电脑 → FHD 账号登录 → 同步与原生 AI 对话

```bat
gradlew.bat assemblePersonalDebug assembleEnterpriseDebug
```

## Release 正式签名

```powershell
cd ..
powershell -File scripts/package/new-android-release-keystore.ps1
powershell -File scripts/package/build-android-release-signed.ps1 -Stage -Version 8.0.0 -AndroidVersion 1.3.0
```

详见 `signing/README.md` 与 `keystore.properties.example`。

产出：`release/packages-v8.0.0/personal|enterprise/` 下的 Windows 安装包与 Android APK。
