# xcagi-core-workflow-employees

## Mod 是房子，员工是家具

| 概念 | 本包中的对应物 | 说明 |
|------|----------------|------|
| **Mod** | 本目录 + `manifest.json` | 可安装单元：路由入口、版本、依赖、可选前端；相当于「房子」。 |
| **员工** | `workflow_employees[]` 每一项 + `backend/employees/*.py` | 副窗名片与 `run()` 实现；相当于「家具」，必须装在 Mod 里。 |

未安装本 Mod 时，FHD 宿主不再内置四名核心工作流员工（`label_print` 等）；请从 MODstore 源码库同步或导入本包。

## 四名员工（家具清单）

| id | 文件 | 职责摘要 |
|----|------|----------|
| `label_print` | `employees/label_print.py` | 星标微信 → 标签/打印信号 |
| `shipment_mgmt` | `employees/shipment_mgmt.py` | 出货单、打印后审计 |
| `receipt_confirm` | `employees/receipt_confirm.py` | 收货/对账类客户反馈 |
| `wechat_msg` | `employees/wechat_msg.py` | 星标轮询、意图、任务列表 |

前端副窗事件链（`xcagi:workflow-*`）仍在宿主；本 Mod 后端提供 **状态/审计/占位 run** 与 manifest 名片，供平台制作与逐步下沉逻辑。

## 文档

- [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) — 现网验收步骤
- [PACKAGE_DECISION.md](PACKAGE_DECISION.md) — 为何 1 Mod + 4 员工
