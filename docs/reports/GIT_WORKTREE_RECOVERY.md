# Git 工作树恢复指南（迁移/重组期）

## 症状

- `git status` 报：`fatal: not a git repository: E:/FHD/.git/worktrees/...`
- 或大量 `D` / `??`，与 IDE 里实际文件不一致
- 仓库根在 **`E:\XCMAX\FHD`**（独立 `.git` 目录），勿与旧路径 `E:\FHD` 混用
- IDE 显示 **~900+ 变更**，但 `cd FHD && git status --short | measure` 只有几十行：多数是 **`XCAGI/` 子模块**内未提交；其中 **`app/`（junction → 根 `app/`）与 `frontend/` 副本仍被索引** 时，父仓库一改 `app/` 子模块会整树显示为修改

### 子模块脏树快修（2026-05）

```powershell
cd E:\XCMAX\FHD\XCAGI
# 权威代码在 monorepo 根 ../app、../frontend；子模块只保留入口/mods/run.py 等
git rm -r --cached app frontend   # 若尚未做；并确保 .gitignore 含 /app 与 /frontend
git add -u && git commit -m "chore: sync XCAGI shell after monorepo migration"
cd E:\XCMAX\FHD
git add XCAGI && git commit -m "chore: bump XCAGI submodule pointer"
```

本地 junction：`powershell -File scripts/ensure_xcagi_app_link.ps1`

## 安全诊断

在 PowerShell 中：

```powershell
cd E:\XCMAX\FHD
git rev-parse --show-toplevel
git status -sb
git diff --stat HEAD
```

若 `rev-parse` 失败，检查 `.git` 是否为目录且完整（非损坏的 worktree 指针）。

**已知的 prunable worktree 修复**（`E:/FHD` → `E:/XCMAX/FHD`）：

```powershell
# .push-v5-worktree/.git 与 .git/worktrees/-push-v5-worktree/gitdir 改为 XCMAX 路径
git worktree prune -v
git status -sb
```

或运行：`scripts/dev/git_change_inventory.ps1` 生成 `git-change-inventory.txt`。

## 推荐流程

1. **冻结迁移批次**：先提交「构建可绿」变更（generic glob、测试修复），再处理大规模 `D`/`??`。
2. **区分三类变更**  
   - 预期删除（已迁到 `XCAGI/`、`mods/`）→ `git add -u`  
   - 误删 → `git checkout HEAD -- <path>` 或从备份恢复  
   - 新文件 → 按目录分批 `git add`
3. **勿在脏树上 force push**；需要备份时：`git stash push -u -m "pre-migration"` 或复制整个 `FHD` 目录。

## 辅助脚本

```powershell
.\scripts\dev\git_status_safe.ps1
```

（输出 top-level、简短 status、未跟踪数量。）

## 与 CI 的关系

GitHub remote：`https://github.com/42433422/ai-excel-helper.git`（见 `.git/config`）。  
推送前在本地跑：`CI_STABLE_ONLY=1` pytest + `npm run build:generic`。
