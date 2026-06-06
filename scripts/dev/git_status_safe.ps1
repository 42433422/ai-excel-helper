# 在 FHD 仓库根输出可读的 git 状态（避免 worktree 路径混淆）
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root
Write-Host "repo root: $root"
try {
    $top = git rev-parse --show-toplevel 2>&1
    Write-Host "git top-level: $top"
    git status -sb
    $untracked = (git ls-files --others --exclude-standard | Measure-Object -Line).Lines
    Write-Host "untracked files: $untracked"
} catch {
    Write-Host "git failed: $_"
    Write-Host "See docs/reports/GIT_WORKTREE_RECOVERY.md"
    exit 1
}
