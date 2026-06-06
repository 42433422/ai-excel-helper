param(
  [string]$Version = '8.0.0',
  [ValidateSet('personal', 'enterprise', 'all')]
  [string]$ProductSku = 'all',
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$Version = $Version.TrimStart('v', 'V')

$hostName = $env:XCAGI_UPDATE_SSH_HOST
$sshUser = $env:XCAGI_UPDATE_SSH_USER
$remoteBase = $env:XCAGI_UPDATE_SSH_PATH
$sshKey = $env:XCAGI_UPDATE_SSH_KEY

if (-not $hostName -or -not $sshUser -or -not $remoteBase) {
  throw @"
缺少上传环境变量（勿写入 git）:
  XCAGI_UPDATE_SSH_HOST
  XCAGI_UPDATE_SSH_USER
  XCAGI_UPDATE_SSH_PATH   例: /var/www/update/releases/stable
可选: XCAGI_UPDATE_SSH_KEY  私钥路径
"@
}

$releaseRoot = Join-Path $Root "release\xcagi-v$Version"
if (-not (Test-Path $releaseRoot)) {
  throw "本地 release 不存在: $releaseRoot — 请先 build-all-skus.ps1"
}

$skus = if ($ProductSku -eq 'all') { @('personal', 'enterprise') } else { @($ProductSku) }
$sshTarget = "${sshUser}@${hostName}"
$rsyncSsh = 'ssh'
if ($sshKey) {
  $keyPath = Resolve-Path $sshKey
  $rsyncSsh = "ssh -i `"$keyPath`" -o StrictHostKeyChecking=accept-new"
}

foreach ($sku in $skus) {
  $localDir = Join-Path $releaseRoot $sku
  if (-not (Test-Path $localDir)) {
    throw "缺少 SKU 目录: $localDir"
  }
  $remoteDir = "$($remoteBase.TrimEnd('/'))/$sku/"
  $files = @(
    Get-ChildItem $localDir -Filter 'XCAGI-*-Setup-*-x64.exe' -File -ErrorAction SilentlyContinue
    Get-ChildItem $localDir -Filter 'latest.yml' -File -ErrorAction SilentlyContinue
    Get-ChildItem (Join-Path $localDir 'tools') -Filter 'XcagiDownloader.exe' -File -ErrorAction SilentlyContinue
  ) | Where-Object { $_ }
  if (-not $files) {
    throw "$sku 目录无待上传文件"
  }

  Write-Host "Upload $sku -> $sshTarget`:$remoteDir"
  $rsyncArgs = @(
    '-avz',
    '--progress',
    '--chmod=D755,F644',
    '-e', $rsyncSsh,
    "$localDir/",
    "${sshTarget}:${remoteDir}"
  )
  if ($DryRun) {
    Write-Host "DRY RUN: rsync $($rsyncArgs -join ' ')"
    continue
  }
  & rsync @rsyncArgs
  if ($LASTEXITCODE -ne 0) {
    throw "rsync failed for SKU $sku (exit $LASTEXITCODE)"
  }
  $setup = $files | Where-Object { $_.Extension -eq '.exe' -and $_.Name -like 'XCAGI-*-Setup-*' } | Select-Object -First 1
  if ($setup) {
    $url = "https://update.xcagi.com/releases/stable/$sku/$($setup.Name)"
    Write-Host "  Public URL (verify): $url"
  }
}

Write-Host 'Upload complete.'
