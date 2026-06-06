param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('personal', 'enterprise')]
  [string]$ProductSku
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$modsRoot = Join-Path $Root "mods"
$stageDir = Join-Path $Root "build\staged-mods-$ProductSku"

$readProfileScript = Join-Path $PSScriptRoot "read-host-profile-stage-ids.py"
$idsJson = (& python $readProfileScript $ProductSku) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "read-host-profile-stage-ids.py failed" }
$parsedIds = $idsJson | ConvertFrom-Json
$ids = @()
foreach ($id in $parsedIds) {
  $ids += [string]$id
}

$excludeAlways = @('taiyangniao-pro', 'sz-qsm-pro', '_employees', 'industry-solutions')

if (Test-Path $stageDir) {
  Remove-Item $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stageDir | Out-Null

foreach ($modId in $ids) {
  if ($excludeAlways -contains $modId) { continue }
  $src = Join-Path $modsRoot $modId
  if (-not (Test-Path $src)) {
    Write-Warning "Mod not found, skip: $modId ($src)"
    continue
  }
  $dst = Join-Path $stageDir $modId
  Copy-Item -Path $src -Destination $dst -Recurse -Force
  Write-Host "Staged: $modId"
}

Write-Host "Staged $($ids.Count) mod(s) for SKU $ProductSku -> $stageDir"
