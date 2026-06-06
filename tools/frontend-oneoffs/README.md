# 前端一次性修补说明（历史）

曾有人在 `frontend/src/` 下放置 `fix_app_vue.py` / `_fix_app_vue.py`，用于向 `App.vue` 注入 `GlobalReadTokenPrompt` 组件；脚本含本机绝对路径，不适合纳入版本控制中的可执行流程。

**当前状态**：`GlobalReadTokenPrompt` 已直接合入 [`frontend/src/App.vue`](../../frontend/src/App.vue)。后续修改请走正常 PR、`npm run lint` 与 `npm run build`，勿在 `src/` 下添加 patch 脚本。
