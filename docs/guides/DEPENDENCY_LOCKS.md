# Python 依赖锁定与可重复构建

## 问题

主依赖声明在 [`XCAGI/requirements.txt`](../../XCAGI/requirements.txt)（及根目录可能存在的约束文件）；**未提交完整 lockfile** 时，不同时间 `pip install` 可能解析到不同次版本，导致「本地可运行、CI/生产不一致」。

## 已纳入版本控制的锁定文件

仓库包含 **[`XCAGI/requirements.lock.txt`](../../XCAGI/requirements.lock.txt)**（由 `pip-compile` 根据 `XCAGI/requirements.txt` 生成，pip 可直接安装）。

## 方案 A：pip-tools（当前采用）

### 重新生成锁定文件（维护者本地）

```bash
python -m pip install pip-tools
python -m piptools compile XCAGI/requirements.txt -o XCAGI/requirements.lock.txt --resolver=backtracking
```

升级依赖：先改 `requirements.txt`，再执行上述命令并提交 `requirements.lock.txt` 的 diff。

### CI / 安装

```bash
pip install -r XCAGI/requirements.lock.txt
```

CI 中 **`.github/workflows/test.yml`** 的 `requirements-lock-consistency` 任务会在 PR 上重跑 `pip-compile` 并与 `requirements.lock.txt` diff，防止漂移。

## 方案 B：uv（可选）

若已安装 [uv](https://docs.astral.sh/uv/)：

```bash
uv pip compile XCAGI/requirements.txt -o XCAGI/requirements.lock.txt
uv pip sync XCAGI/requirements.lock.txt
```

与 pip-tools **二选一维护即可**，避免两套流程并行未同步。

## Poetry 替代路径

若团队统一 Poetry：将依赖迁入 `pyproject.toml` 的 `[project.dependencies]`，使用 `poetry lock` 生成 `poetry.lock`，并在 CI 中 `poetry install --no-root`。与 uv **二选一**，避免双套锁定并存。

## 与 `pyproject.toml` 的关系

根目录与 `XCAGI/pyproject.toml` 中 `[project] dependencies = []` 为占位；**当前真实源仍为 `XCAGI/requirements.txt`**，锁定文件应对齐该文件。
