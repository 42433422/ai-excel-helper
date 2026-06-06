param(
  [ValidateSet('pre', 'post')]
  [string]$Phase = 'pre',
  [string]$Version = '8.0.0'
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root
$Version = $Version.TrimStart('v', 'V')
$erpMod = 'xcagi-erp-domain-bridge'
$excludedMods = @('taiyangniao-pro', 'sz-qsm-pro', '_employees', 'industry-solutions')

function Fail([string]$msg) {
  Write-Error "[pre-release-security] $msg"
}

function Scan-SecretsInTree {
  param([string]$Dir, [string]$Label)
  if (-not (Test-Path $Dir)) { return }
  $hits = Get-ChildItem -Path $Dir -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Name -match '\.env$' -and $_.Name -ne '.env.example' -or
      $_.Name -match 'secret|private_key' -or
      $_.Extension -in @('.pem', '.key')
    } |
    Where-Object {
      $_.FullName -notmatch '\\node_modules\\' -and
      $_.FullName -notmatch '\\.git\\'
    }
  foreach ($h in $hits) {
    Fail "${Label} sensitive file: $($h.FullName)"
  }
}

function Test-StagedSku {
  param([string]$Sku, [bool]$ExpectErp)
  & "$PSScriptRoot\stage-bundled-mods.ps1" -ProductSku $Sku | Out-Null
  $stage = Join-Path $Root "build\staged-mods-$Sku"
  if (-not (Test-Path $stage)) {
    Fail "staging failed: $stage"
  }
  $hasErp = Test-Path (Join-Path $stage $erpMod)
  if ($ExpectErp -and -not $hasErp) {
    Fail "SKU $Sku must include $erpMod"
  }
  if (-not $ExpectErp -and $hasErp) {
    Fail "SKU $Sku must NOT include $erpMod"
  }
  foreach ($bad in $excludedMods) {
    if (Test-Path (Join-Path $stage $bad)) {
      Fail "SKU $Sku staged excluded mod: $bad"
    }
  }
  Write-Host "OK staged $Sku (erp=$hasErp)"
}

if ($Phase -eq 'pre') {
  Write-Host '=== Pre-build security scan ==='
  Scan-SecretsInTree (Join-Path $Root 'mods') 'mods/'
  Scan-SecretsInTree (Join-Path $Root 'config') 'config/'
  Scan-SecretsInTree (Join-Path $Root 'resources') 'resources/'
  $dotEnv = Join-Path $Root '.env'
  if (Test-Path $dotEnv) {
    Write-Warning 'Root .env exists; PyInstaller spec must ship only .env.example'
  }
  Test-StagedSku 'personal' $false
  Test-StagedSku 'enterprise' $true
  & "$PSScriptRoot\verify-desktop-database-default.ps1"
  Write-Host 'Pre-build security: PASSED'
  exit 0
}

Write-Host '=== Post-build security scan ==='
$releaseRoot = Join-Path $Root "release\xcagi-v$Version"
if (-not (Test-Path $releaseRoot)) {
  Fail "release dir missing: $releaseRoot (run build-all-skus first)"
}

$legacy = Get-ChildItem $releaseRoot -Filter 'XCAGI-Setup-*.exe' -File -ErrorAction SilentlyContinue
if ($legacy) {
  Fail "release 根目录不得放置 legacy 单包（请仅保留 personal/enterprise 子目录）: $($legacy.Name -join ', ')"
}
$flatSku = Get-ChildItem $releaseRoot -Filter 'XCAGI-*-Setup-*-x64.exe' -File -ErrorAction SilentlyContinue
if ($flatSku) {
  Fail "安装包必须位于 SKU 子目录内，不得放在 release 根: $($flatSku.Name -join ', ')"
}

foreach ($sku in @('personal', 'enterprise')) {
  $skuDir = Join-Path $releaseRoot $sku
  if (-not (Test-Path $skuDir)) {
    Fail "missing SKU dir: $skuDir"
  }
  $modsDir = Join-Path $skuDir 'win-unpacked\resources\backend\_internal\mods'
  if (Test-Path $modsDir) {
    & "$PSScriptRoot\verify-bundled-mods.ps1" -ProductSku $sku -UnpackedDir $modsDir
    Scan-SecretsInTree $modsDir "built-mods-$sku"
  } else {
    Write-Warning "win-unpacked mods dir not found: $modsDir"
  }
  $skuJson = Join-Path $skuDir 'win-unpacked\resources\product-sku.json'
  if (Test-Path $skuJson) {
    $meta = Get-Content $skuJson -Raw | ConvertFrom-Json
    if ($meta.sku -ne $sku) {
      Fail "product-sku.json sku=$($meta.sku) != folder $sku"
    }
  }
  $setup = Get-ChildItem $skuDir -Filter 'XCAGI-*-Setup-*-x64.exe' -File -ErrorAction SilentlyContinue |
    Select-Object -First 1
  $yml = Join-Path $skuDir 'latest.yml'
  if (-not $setup) { Fail "$sku missing Setup exe" }
  if (-not (Test-Path $yml)) { Fail "$sku missing latest.yml" }
  Write-Host "OK $sku artifact: $($setup.Name)"
}

Write-Host 'Post-build security: PASSED'
