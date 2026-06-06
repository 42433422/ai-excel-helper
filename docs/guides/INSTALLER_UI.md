# XCAGI Windows 安装包（单文件 · 360 风格）

> 用户只需 **`XCAGI-Setup-{version}-x64.exe`** 一个文件。WPF 自定义向导内嵌 NSIS 静默包。

---

## 视觉规范

| 元素 | 规格 |
|------|------|
| 窗口 | 920×560，圆角 12px，外阴影 |
| 字体 | Microsoft YaHei UI |
| 主色 | `#1A9FFF` → `#0B7AE8` 渐变（主按钮、进度条） |
| 成功色 | `#12B76A`（完成页、完成按钮） |
| 侧栏 | 320px 天蓝渐变 + 装饰圆 + Logo 阴影卡片 |
| 步骤轨 | 竖向圆点 + 连接线（`StepRailItem`） |
| 主按钮 | 高 42px，圆角 21px（胶囊），hover 微缩放 |
| 内容卡片 | 圆角 12px + 轻阴影 |

---

## 体验流程

```text
欢迎 → 许可协议 → 安装位置 → 解压（首次）→ 静默安装 → 完成
```

左侧步骤轨同步高亮当前步；欢迎页含三列能力说明与可选右侧 hero 插画。

---

## 打包

```powershell
cd <repo-root>
powershell -File scripts/package/build-all-skus.ps1 -Version 8.0.0
```

```text
release/xcagi-v8.0.0/
  personal/XCAGI-Personal-Setup-8.0.0-x64.exe + latest.yml + tools/
  enterprise/XCAGI-Enterprise-Setup-8.0.0-x64.exe + latest.yml + tools/
```

生成安装图与 hero 插画：

```powershell
python scripts/package/generate-desktop-resources.py
```

---

## 源码

| 路径 | 作用 |
|------|------|
| `tools/XcagiInstaller/Themes/InstallerTheme.xaml` | 全局样式 |
| `tools/XcagiInstaller/Controls/StepRailItem.*` | 左侧步骤轨 |
| `tools/XcagiInstaller/MainWindow.xaml` | 主界面 |
| `tools/XcagiInstaller/Assets/installer-hero.png` | 欢迎页插画（可选） |
| `scripts/package/generate-desktop-resources.py` | 生成 hero / NSIS 位图 |

---

*配套：[DELIVERABLE_PRODUCT.md](../DELIVERABLE_PRODUCT.md)*
