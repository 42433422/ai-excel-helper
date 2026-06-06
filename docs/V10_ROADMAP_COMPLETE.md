# v10 路线图收口完成说明（2026-06-04）

本分支 `chore/v10-roadmap-complete`（基于 `chore/v10-shim-closeout` / PR 1.1）落地路线图 **阶段 1–3** 全部代码改动。

## 阶段 1 · shim 收口

| PR | 状态 | 说明 |
|----|------|------|
| 1.1 | `chore/v10-shim-closeout` | 删除 `legacy_host_routers.py`，内联 `register_legacy_gap_routers` |
| 1.2 | 本分支 | `LEGACY_ROUTE_REGISTRY` → 14 域文档表；`verify_registry_integrity` 仅磁盘白名单 |

## 阶段 2 · SLO 闭环

| PR | 改动 |
|----|------|
| 2.1 | `middleware_extra.register_http_sli_middleware` + `factory.init_metrics`；`auth_login_duration_seconds` / `chat_stream_first_byte_seconds` |
| 2.2 | `k8s/monitoring/prometheus/recording_rules.yml` + `SLOBudgetBurningFast` |
| 2.3 | `sla-probe.yml` 去掉 frontend-sla `|| true` |
| 2.4 | `deploy.yml` canary rollback 增加 `kubectl rollout undo`；Helm `XCAGI_RELEASE_SLO_HALT` / `LLM_*` |

## 阶段 3 · AI 可插拔

| PR | 改动 |
|----|------|
| 3.1–3.2 | `app/infrastructure/llm/providers/*` + `LLMProviderRegistry` |
| 3.3 | `ConversationAPI.call_llm_api` → registry |
| 3.4 | intent / distillation / product_parser / planner / engine / ai_chat 等去硬编码 URL |
| 3.5 | `POST /api/admin/llm/reload`；`record_ai_call` 接 Provider |

## 推送

```bash
bash /tmp/ship-v10-roadmap-all.sh master
```

## 仍需人工（凭据/管理员）

1. `main` 与 `master` ruleset / Release gate 对齐（见上一轮说明）
2. Alertmanager webhook 替换为真实通道（`k8s/monitoring/alertmanager/alertmanager.yml`）
3. 本地 1605+ 脏文件 triage 后再在脏 worktree 上 cherry-pick
