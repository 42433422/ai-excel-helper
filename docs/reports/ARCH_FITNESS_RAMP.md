# 架构体检分阶段收敛（ARCH_FITNESS_RAMP）

## 现状（2026-05）

| 类别 | 数量 | 策略 |
|------|------|------|
| `routes → app.services` | **0（新违例门禁）** | 路由仅 `app.application.*` 门面 |
| `giant-file` (>500 行) | **52（基线登记）** | 按模块拆分，基线只减不增 |
| `domain → infrastructure` | 0 | 保持 |

运行：`python scripts/arch_fitness.py`  
- 命中基线 → 不失败  
- **新增**违例 → exit 1  

基线文件：`scripts/arch_fitness_baseline.txt`

## 阶段 A（已完成）

- [x] 9 处路由直连 services → `app/application/*_app.py` 门面
- [x] `arch_fitness.py` 基线 + 新违例门禁

## 阶段 B（进行中）

按优先级拆分巨型文件（每次 PR 至少减 1 条基线）：

1. `fastapi_routes/legacy_auth.py`、`approval.py`
2. `application/ai_chat_app_service.py`（按用例拆子模块）
3. `services/intent_service.py` → 规则引擎 / LLM 适配器分离

## 阶段 C

- CI 增加 `python scripts/arch_fitness.py`（与 pytest 并行）
- 季度目标：giant-file 基线从 52 → 30
