# FrontendEdition: generic = 默认通用壳（ADCDFG）；full = 完整 ERP 侧栏
param(
  [string]$Version = "8.0.0",
  [switch]$SkipFrontend,
  [ValidateSet('full', 'generic', 'minimal')]
  [string]$FrontendEdition = 'generic',
  [ValidateSet('personal', 'enterprise', '')]
  [string]$ProductSku = ''
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$Version = $Version.TrimStart("v", "V")

$skuFrontendMap = @{
  personal = 'minimal'
  enterprise = 'full'
}
if ($ProductSku) {
  if (-not $skuFrontendMap.ContainsKey($ProductSku)) {
    throw "Unknown ProductSku: $ProductSku"
  }
  $FrontendEdition = $skuFrontendMap[$ProductSku]
  & "$PSScriptRoot\stage-bundled-mods.ps1" -ProductSku $ProductSku
}

if (-not $SkipFrontend) {
  Push-Location (Join-Path $Root "frontend")
  if (-not (Test-Path "node_modules")) {
    npm install
  }
  if ($FrontendEdition -eq 'minimal') {
    npm run build:minimal
  } elseif ($FrontendEdition -eq 'full') {
    npm run build:full
  } else {
    npm run build
  }
  Pop-Location
}

python -m pip install --upgrade pip
$RuntimeRequirements = Join-Path $env:TEMP "xcagi-runtime-requirements.txt"
Get-Content "XCAGI\requirements.txt" |
  Where-Object { $_ -notmatch '^\s*pytest($|[-=<>])' } |
  Set-Content -Path $RuntimeRequirements -Encoding UTF8
python -m pip install -r $RuntimeRequirements
python -m pip install "pyinstaller>=6.0" appdirs

$env:XCAGI_VERSION = $Version
if ($ProductSku) {
  $env:XCAGI_PRODUCT_SKU = $ProductSku
}
& "$PSScriptRoot\write-version.ps1" -Version $Version
if ($ProductSku) {
  $stageDir = Join-Path $Root "build\staged-mods-$ProductSku"
  if (Test-Path $stageDir) {
    $env:XCAGI_STAGED_MODS_DIR = $stageDir
    $env:XCAGI_MODS_ROOT = $stageDir
    python "$PSScriptRoot\generate_mods_index.py"
    if ($LASTEXITCODE -ne 0) { throw "generate_mods_index.py failed" }
  }
}
python -m PyInstaller --noconfirm --clean "scripts\package\xcagi_backend.spec"
if ($ProductSku) {
  Remove-Item Env:XCAGI_STAGED_MODS_DIR -ErrorAction SilentlyContinue
}

Write-Host "Backend build complete: dist\xcagi-backend"
