# XCAGI 单文件安装程序（360 风格 WPF）

对外仅一个 **`XCAGI-Setup-{version}-x64.exe`**：自定义安装界面 + 内嵌 NSIS 静默包。首次点击「开始安装」时解压到 `%LOCALAPPDATA%\XCAGI\installer-cache\`，再静默安装。

## 正式打包

```powershell
powershell -File scripts/package/build-all-skus.ps1 -Version 8.0.0
```

输出：`release/xcagi-v8.0.0/{personal,enterprise}/XCAGI-*-Setup-8.0.0-x64.exe`

## 本地调试（不内嵌）

将 `XCAGI-Setup-*.exe` 放在 `bin/Debug/net8.0-windows/` 同目录后：

```powershell
dotnet run --project tools/XcagiInstaller/XcagiInstaller.csproj
```
