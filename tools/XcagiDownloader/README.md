# XCAGI 安装包下载器（Windows）

体量小于完整桌面壳，用于在内网镜像、系统代理或应用内更新异常时，按 **electron-builder generic** 约定拉取 **`latest.yml`**、可选校验 **Ed25519**（与桌面 `XCAGI_UPDATE_ED25519_PUBLIC_KEY` 一致）、**断点下载**完整 NSIS 安装包并校验 **SHA512**。

## 构建

```powershell
# 自包含单文件（推荐随桌面发行版一并分发）
dotnet publish .\XcagiDownloader.csproj -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true `
  -p:IncludeNativeLibrariesForSelfExtract=true `
  -p:EnableCompressionInSingleFile=true `
  -o ..\..\release\xcagi-v8.0.0\enterprise\tools
```

Windows 安装流水线会在 `scripts/package/build-installer.ps1` 末尾自动执行上述发布（输出到 `release/xcagi-v{version}/{personal|enterprise}/tools/XcagiDownloader.exe`）。

## 使用说明

| 配置项 | 含义 |
|--------|------|
| **Base URL** | 与桌面环境变量 **`XCAGI_UPDATE_URL`** 相同：指向包含 **`latest.yml`** 与 **`XCAGI-Setup-*.exe`** 的目录（末尾可有或无 `/`）。 |
| **系统代理 / 手动代理** | 手动代理示例：`http://127.0.0.1:7890`。仅勾选系统代理且留空手动代理时，使用 IE/系统代理设置。 |
| **Ed25519 公钥 PEM** | 与 **`XCAGI_UPDATE_ED25519_PUBLIC_KEY`** 相同；若填写则要求 `latest.yml` 含 `signature: ed25519:` 且验签通过。 |
| **保存目录** | 最终安装包路径：`{保存目录}\{latest.yml 中 files[0].url 文件名}`。 |

临时文件：`{目标文件名}.partial`，SHA512 失败时会保留便于排查。

日志与配置：`%AppData%\XCAGI\downloader\`（`downloader.log`、`settings.json`）。

## 内网镜像目录结构（与更新站一致）

客户只需把官方 stable 目录 mirror 到内网 HTTP(S) 服务，例如：

- `https://intranet.example/xcagi/releases/stable/latest.yml`
- `https://intranet.example/xcagi/releases/stable/XCAGI-Setup-8.0.0-x64.exe`
- （可选）同目录 `*.blockmap` 供主程序 electron-updater 差分更新；下载器只用 yml + Setup。

将下载器中 **Base URL** 设为 `https://intranet.example/xcagi/releases/stable` 即可。

## NSIS / electron-builder 静默安装（IT 脚本）

electron-builder 生成的 NSIS 安装包常见参数包括：

- **`/S`**：静默安装（无 UI，具体子选项因 NSIS 脚本而异）。
- **`/currentuser`**：当前用户安装（与当前默认 `perMachine: false` 一致）。
- **`/allusers`**：若安装包支持时的每计算机安装模式。

**务必在目标环境实测**：客户环境杀毒、组策略与自定义 `installer.nsh` 可能影响参数行为。下载器 UI 提供「运行安装包」使用交互模式；批量部署建议由 IT 使用供应商确认的静默命令行。

## 与桌面自动更新的关系

- 主程序仍使用 **electron-updater**；下载器为 **兜底**：首装拷盘、代理/证书问题、元数据签名校验策略与桌面一致。
- 二者共用同一 **`latest.yml`** 与安装包 URL，无需第二套版本清单。
