# Assert desktop delivery uses SQLite baseline (no postgres .env in PyInstaller tree; Electron --desktop).
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

function Fail([string]$msg) {
  Write-Error "[verify-desktop-database-default] $msg"
}

Write-Host '=== verify-desktop-database-default ==='

$specPath = Join-Path $Root 'scripts\package\xcagi_backend.spec'
if (-not (Test-Path $specPath)) {
  Fail "missing $specPath"
}
$specText = Get-Content $specPath -Raw
if ($specText -notmatch '\.env\.example') {
  Fail 'xcagi_backend.spec must bundle .env.example only'
}
if ($specText -match '(?m)^\s*["'']\.env["'']') {
  Fail 'xcagi_backend.spec must not bundle .env'
}

$desktopMain = Join-Path $Root 'desktop\main.ts'
if (-not (Test-Path $desktopMain)) {
  Fail "missing $desktopMain"
}
$mainText = Get-Content $desktopMain -Raw
if ($mainText -notmatch '--desktop') {
  Fail 'desktop/main.ts must pass --desktop to backend'
}

$distBackend = Join-Path $Root 'dist\xcagi-backend'
if (Test-Path $distBackend) {
  $badEnv = Get-ChildItem -Path $distBackend -Recurse -File -Filter '.env' -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq '.env' }
  foreach ($f in $badEnv) {
    $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match 'postgresql') {
      Fail "dist backend contains postgres .env: $($f.FullName)"
    }
  }
  $internal = Join-Path $distBackend '_internal'
  if (Test-Path $internal) {
    Get-ChildItem -Path $internal -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -eq '.env' -and $_.Name -ne '.env.example' } |
      ForEach-Object {
        $c = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
        if ($c -match 'postgresql') {
          Fail "PyInstaller tree ships postgres credentials: $($_.FullName)"
        }
      }
  }
}

Write-Host 'verify-desktop-database-default: PASSED'
