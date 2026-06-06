"""start-lan.ps1 启动器：Stop-Existing 不得长时间阻塞（回归 WMI 卡死）。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_PWSH = shutil.which("pwsh")


REPO = Path(__file__).resolve().parents[1]
PS1 = REPO / "scripts" / "launchers" / "start-lan.ps1"


@pytest.mark.skipif(
    not _PWSH, reason="start-lan.ps1 需 pwsh（UTF-8 BOM）；Windows PowerShell 5.1 会解析失败"
)
def test_stop_only_skip_kill_exits_quickly():
    """仅停止且跳过杀进程时应秒级退出（不进入长循环）。"""
    r = subprocess.run(
        [
            _PWSH,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "-StopOnly",
            "-SkipKillExisting",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)


def test_stop_existing_enumeration_and_path_reads_are_quick():
    """与 Stop-Existing 相同：Get-Process 通配符 + .Path 判定；不在单测里调 WMI（Get-CimInstance 可能整段阻塞，无法被 25s 预算打断）。"""
    repo = str(REPO).replace("'", "''")
    script = r"""
$RepoRoot = '__REPO__'
$sw = [Diagnostics.Stopwatch]::StartNew()
$byId = @{}
foreach ($pat in @('python*', 'node*')) {
    try {
        foreach ($g in @(Get-Process -Name $pat -ErrorAction SilentlyContinue)) { $byId[$g.Id] = $g }
    } catch { }
}
$sw.Stop()
if ($sw.ElapsedMilliseconds -gt 20000) { throw "Get-Process phase too slow: $($sw.ElapsedMilliseconds)ms" }
$rootNorm = ''
try {
    $rootNorm = ((Resolve-Path -LiteralPath $RepoRoot).ProviderPath).TrimEnd('\')
} catch {
    $rootNorm = $RepoRoot.TrimEnd('\')
}
$pathMs = 0
$n = 0
foreach ($gp in $byId.Values | Select-Object -First 200) {
    $t0 = [Diagnostics.Stopwatch]::StartNew()
    try {
        $fp = $gp.Path
        if ($fp -and $rootNorm -and ($fp.StartsWith($rootNorm, [System.StringComparison]::OrdinalIgnoreCase))) { $n++ }
    } catch { }
    $t0.Stop()
    $pathMs += $t0.ElapsedMilliseconds
    if ($pathMs -gt 20000) { throw ".Path phase too slow: $($pathMs)ms" }
}
Write-Host "OK enumMs=$($sw.ElapsedMilliseconds) pathMs=$pathMs repoHits=$n total=$($byId.Count)"
""".replace(
        "__REPO__",
        repo,
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
    out = (r.stdout or "") + (r.stderr or "")
    assert "OK " in out, out
