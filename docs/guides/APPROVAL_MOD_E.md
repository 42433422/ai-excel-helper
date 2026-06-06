# 里程碑 E：审批门面 Mod

- Mod：`xcagi-approval-bridge` v1.1+
- 门面：`/api/mod/xcagi-approval-bridge/*`
- 宿主：`/api/approval/*`（兼容保留）

前端 `approval.ts` 安装 Mod 后走 `resolveApprovalApiPath()`。

环境变量：`XCAGI_APPROVAL_VIA_MOD=1` / `XCAGI_DISABLE_APPROVAL_MOD=1`
