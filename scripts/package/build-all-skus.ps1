param(
  [string]$Version = "8.0.0",
  [switch]$SkipUiInstaller
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Version = $Version.TrimStart("v", "V")
$releaseRoot = Join-Path $Root "release\xcagi-v$Version"

foreach ($sku in @('personal', 'enterprise')) {
  New-Item -ItemType Directory -Force -Path (Join-Path $releaseRoot $sku) | Out-Null
}

$readme = @"
XCAGI v$Version — 双 SKU 发行目录

personal/    — XCAGI-Personal-Setup-$Version-x64.exe + latest.yml + tools/
enterprise/  — XCAGI-Enterprise-Setup-$Version-x64.exe + latest.yml + tools/

上传: scripts/package/upload-release-skus.ps1
官网: {BASE}/{personal|enterprise}/{文件名}
"@
Set-Content -Path (Join-Path $releaseRoot "README.txt") -Value $readme -Encoding UTF8

foreach ($sku in @('personal', 'enterprise')) {
  Write-Host "========== Building SKU: $sku =========="
  $args = @(
    '-File', (Join-Path $PSScriptRoot 'build-installer.ps1'),
    '-Version', $Version,
    '-ProductSku', $sku
  )
  if ($SkipUiInstaller) { $args += '-SkipUiInstaller' }
  & powershell @args
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "build-installer failed for SKU $sku (exit $LASTEXITCODE)"
  }
}

Write-Host ""
Write-Host "Both SKUs built:"
Write-Host "  $releaseRoot\personal\"
Write-Host "  $releaseRoot\enterprise\"
