# 打包决策（Mod ≠ 员工）

## 结论

| 层级 | 决策 |
|------|------|
| **Mod（房子）** | 单一包：`xcagi-core-workflow-employees` v1.0.0 |
| **员工（家具）** | 同一 Mod 内 4 名 `workflow_employees`，各对应 `backend/employees/<stem>.py` |

**不采用** 4 个独立 Mod（四栋房子各放一件家具）——同步次数多、版本难对齐、副窗 `localStorage` 键与宿主约定 id 仍须全局一致。

## 与 artifact 类型

- 本包为 **`artifact: mod`（默认）**，不是 `employee_pack`。
- `employee_pack` 是「只有一件家具、没有房子菜单」的全局单员工 zip（`mods/_employees/`）。
- 本包四名员工住在 **同一栋房子** 的 `workflow_employees[]` 里，由 `blueprints.py` 统一挂 `/api/mod/xcagi-core-workflow-employees/employees/{id}/run`。

## 宿主依赖

- `dependencies.xcagi >= 8.0.0`
- 安装路径：`mods/xcagi-core-workflow-employees/`（同步到 FHD `XCAGI/mods/`）
