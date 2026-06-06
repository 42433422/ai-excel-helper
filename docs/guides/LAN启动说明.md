# XCAGI v8.0 局域网启动说明

## 快速启动

> **版本**：与 **XCAGI v8.0**（FastAPI + Vite 局域网联调）一致；脚本标题与控制台横幅会显示 `v8.0`。
> **路径变更说明(2026-04 重组后)**:启动脚本已从仓库根迁移到 `scripts/launchers/`。
> 脚本内部会自动从自身位置反推仓库根,不再依赖硬编码的 `E:\FHD` 路径。

### 方式一:双击运行(推荐)
双击 `scripts\launchers\start-lan.bat` → 选择菜单选项 → 自动启动

`scripts/launchers/` 下的 `start-lan.bat - 快捷方式.lnk` 已更新,可放到桌面继续使用。

### 方式二:命令行
```powershell
# 启动前后端
.\scripts\launchers\start-lan.ps1

# 仅启动后端
.\scripts\launchers\start-lan.ps1 -NoFrontend

# 仅启动前端
.\scripts\launchers\start-lan.ps1 -NoBackend

# 关闭热重载(生产模式)
.\scripts\launchers\start-lan.ps1 -NoReload

# 仅停止本仓库相关的 python/node 进程
.\scripts\launchers\start-lan.ps1 -StopOnly
```

## 访问地址

启动成功后会显示以下地址：

| 访问方式 | 地址示例 |
|---------|---------|
| 局域网访问 | `http://192.168.x.x:5001` |
| 本机访问 | `http://localhost:5001` |

## 局域网授权

其他设备首次访问时需要输入密钥：**`61508693`**

## 防火墙设置

如果其他设备无法访问，可能需要添加防火墙规则：

```powershell
# 管理员 PowerShell 运行
New-NetFirewallRule -DisplayName "XCAGI Frontend" -Direction Inbound -LocalPort 5001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "XCAGI Backend" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

## 故障排查

| 问题 | 解决方式 |
|-----|---------|
| 端口被占用 | 运行 `scripts\launchers\start-lan.bat` → 选择 4 停止所有服务,然后重新启动 |
| 热重载不生效 | 检查文件修改是否在 `app/` 目录内 |
| 局域网访问不了 | 检查防火墙设置，确保 5000/5001 端口开放 |
| 授权失败 | 确认输入的是 `61508693`（不是 `61408693`） |
