# Mod 制作页 → FHD 侧栏菜单

在 MODstore 制作页保存 manifest **不会**立刻改变浏览器里已打开的 FHD 侧栏；侧栏在宿主 **下次加载该 Mod** 后更新。

## 数据流

```
MODstore 制作页
  ├─ 行业适配 → manifest.industry
  ├─ 前端 Tab「重新生成」→ manifest.frontend.menu + frontend/routes.js
  └─ 安装/同步到宿主 mods/ 目录
         ↓
FHD 后端 GET /api/mods/ → load_all_mods
         ↓
modsStore.getModMenu() + useVisibleNavItems() 合并 coreMenu
         ↓
Sidebar.vue 渲染 menu-item
```

## 字段与侧栏表现

| 制作页操作 | manifest 字段 | 侧栏效果 |
|------------|-----------------|----------|
| 行业适配并保存 | `industry` | 宿主核心菜单文案（`useIndustryUiText`、`industry` store） |
| 重新生成前端 | `frontend.menu` + `routes.js` | **新增** Mod 菜单项 |
| ERP 等 Mod 配置 | `menu_overrides` | **隐藏**宿主同名核心项，避免与 Mod 重复 |

## 生效条件（通用软件 checklist）

1. **制作端**：向导完成「重新生成前端」，manifest 含 `frontend.menu`。
2. **部署**：Mod 包位于本机 `FHD/mods/<mod-id>/`，后端 `load_all_mods` 无报错。
3. **刷新**：重新登录 FHD，或触发 `modsStore.initialize(true)`；行业可在 **系统设置 → 行业配置** 与 manifest 对齐。

## 与开屏礼盒动画的关系

`startupReveal` + `Sidebar` 的落下动画只控制 **展示时机**，不改变菜单数据来源。

## 本机验证示例

1. 为 mod 填写 `description`、选行业并保存；执行「重新生成前端」。
2. 将包复制到 `FHD/mods/m-<id>/`，重启 `python run.py`。
3. 登录 FHD，开屏结束后侧栏应出现新 menu 项。
