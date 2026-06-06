# 核心工作流 Mod（房子 + 四名家具员工）

## Mod ≠ 员工

| 层级 | id / 路径 | 说明 |
|------|-----------|------|
| **Mod（房子）** | `xcagi-core-workflow-employees` | 可安装包：`manifest.json` + `backend/blueprints.py` |
| **员工（家具）** | `label_print`、`shipment_mgmt`、`receipt_confirm`、`wechat_msg` | 声明在 `manifest.workflow_employees[]`，实现在 `backend/employees/<id>.py` |

源码主库：[成都修茈科技有限公司/mods/xcagi-core-workflow-employees](../../成都修茈科技有限公司/mods/xcagi-core-workflow-employees/README.md)

## 宿主安装位置

- `mods/xcagi-core-workflow-employees/`
- `XCAGI/mods/xcagi-core-workflow-employees/`（运行时挂载）

未安装时，副窗不再显示四名内置员工；请从 MODstore 同步或运行 `scripts/sync_core_workflow_mod_to_fhd.ps1`（平台侧）。

## API

- `GET /api/mod/xcagi-core-workflow-employees/status`
- `POST /api/mod/xcagi-core-workflow-employees/employees/{employee_id}/run`

## 验收

见平台包内 [docs/ACCEPTANCE.md](../../成都修茈科技有限公司/mods/xcagi-core-workflow-employees/docs/ACCEPTANCE.md)
