# 将最新 frontend 构建产物同步到本机已安装的 XCAGI（与网页端 dev 对齐请先 npm run build）
# Edition: generic = 默认通用壳（ADCDFG）；full = 完整 ERP
param(
  [switch]$AlsoWinUnpacked,
  [switch]$Build,
  [ValidateSet('full', 'generic', 'minimal')]
  [string]$Edition = 'generic',
  [ValidateSet('personal', 'enterprise')]
  [string]$ProductSku = 'enterprise',
  [string]$Version = '8.0.0'
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$Src = Join-Path $Root 'templates\vue-dist'

if ($Build -or -not (Test-Path (Join-Path $Src 'index.html'))) {
  Push-Location (Join-Path $Root 'frontend')
  if (-not (Test-Path 'node_modules')) {
    npm install
  }
  if ($Edition -eq 'minimal') {
    npm run build:minimal
  } elseif ($Edition -eq 'full') {
    npm run build:full
  } else {
    npm run build
  }
  Pop-Location
}

if (-not (Test-Path (Join-Path $Src 'index.html'))) {
  throw "Missing vue-dist at $Src — run with -Build or build frontend first."
}

$hash = 'unknown'
$html = Get-Content (Join-Path $Src 'index.html') -Raw -Encoding UTF8
if ($html -match 'index-([A-Za-z0-9]+)\.js') { $hash = $Matches[1] }

$targets = @(
  (Join-Path $env:LOCALAPPDATA 'Programs\XCAGI\resources\backend\_internal\templates\vue-dist'),
  (Join-Path $env:LOCALAPPDATA 'Programs\XCAGI\resources\frontend')
)
if ($AlsoWinUnpacked) {
  $ver = $Version.TrimStart('v', 'V')
  $unpacked = Join-Path $Root "release\xcagi-v$ver\$ProductSku\win-unpacked\resources"
  if (Test-Path $unpacked) {
    $targets += @(
      (Join-Path $unpacked 'backend\_internal\templates\vue-dist'),
      (Join-Path $unpacked 'frontend')
    )
  } else {
    Write-Warning "win-unpacked not found: $unpacked (build with -ProductSku $ProductSku first)"
  }
}

foreach ($dst in $targets) {
  $parent = Split-Path $dst
  if (-not (Test-Path $parent)) { continue }
  if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  robocopy $Src $dst /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $dst (exit $LASTEXITCODE)" }
}

$cacheRoot = Join-Path $env:APPDATA 'xcagi-desktop'
foreach ($sub in @('Cache', 'Code Cache', 'GPUCache')) {
  $p = Join-Path $cacheRoot $sub
  if (Test-Path $p) {
    Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cleared Electron cache: $p"
  }
}

Write-Host "Synced vue-dist (edition=$Edition, index-$hash.js) -> $($targets.Count) path(s)."
Write-Host 'Restart XCAGI from Start Menu.'
Write-Host 'If menu still shows 产品管理/出货记录: Settings -> switch industry to 考勤 (saved profile may be 涂料).'
