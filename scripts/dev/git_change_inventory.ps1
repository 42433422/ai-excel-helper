# 生成 git-change-inventory.txt 并按 D/M/?? 统计（候选稳定态收尾）
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $root

$lines = @(git status --short 2>&1)
$out = Join-Path $root "git-change-inventory.txt"
$lines | Out-File -FilePath $out -Encoding utf8

$deleted = @($lines | Where-Object { $_ -match '^ D' })
$modified = @($lines | Where-Object { $_ -match '^ M' })
$staged = @($lines | Where-Object { $_ -match '^[MADRCU]' -and $_ -notmatch '^ ' })
$untracked = @($lines | Where-Object { $_ -match '^\?\?' })

$summary = @"
# Git change inventory ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))
root: $root

total: $($lines.Count)
deleted (D): $($deleted.Count)
modified (M): $($modified.Count)
untracked (??): $($untracked.Count)

## Deleted paths by top-level
$(
    $deleted | ForEach-Object {
        $p = ($_ -replace '^\s*D\s+', '').Trim()
        if ($p -match '[\\/]') { ($p -replace '\\', '/') -replace '/[^/]+$', '' } else { '.' }
    } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 |
    ForEach-Object { "- $($_.Name): $($_.Count)" }
) -join "`n"

## Modified paths by top-level
$(
    $modified | ForEach-Object {
        $p = ($_ -replace '^\s*M\s+', '').Trim()
        if ($p -match '[\\/]') { ($p -replace '\\', '/') -replace '/[^/]+$', '' } else { '.' }
    } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 |
    ForEach-Object { "- $($_.Name): $($_.Count)" }
) -join "`n"

## Untracked paths by top-level
$(
    $untracked | ForEach-Object {
        $p = ($_ -replace '^\?\?\s+', '').Trim()
        if ($p -match '[\\/]') { ($p -replace '\\', '/') -replace '/[^/]+$', '' } else { '.' }
    } | Group-Object | Sort-Object Count -Descending | Select-Object -First 20 |
    ForEach-Object { "- $($_.Name): $($_.Count)" }
) -join "`n"

See docs/MIGRATION_REGISTRY.md for expected deletions (backend/, flask routes, etc.).
"@

$summaryPath = Join-Path $root "git-change-inventory-summary.md"
$summary | Out-File -FilePath $summaryPath -Encoding utf8
Write-Host "Wrote $out ($($lines.Count) lines)"
Write-Host "Wrote $summaryPath"
