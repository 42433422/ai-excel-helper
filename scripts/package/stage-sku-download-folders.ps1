<#
.SYNOPSIS
  Stage Windows installer + Android APK into per-SKU folders (personal / enterprise).

.EXAMPLE
  powershell -File scripts/package/stage-sku-download-folders.ps1 -Version 8.0.0
#>
param(
  [string]$Version = '8.0.0',
  [string]$AndroidVersion = '1.3.0',
  [switch]$BuildAndroidRelease
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$Version = $Version.TrimStart('v', 'V')

$outRoot = Join-Path $Root "release\packages-v$Version"
$personalDir = Join-Path $outRoot 'personal'
$enterpriseDir = Join-Path $outRoot 'enterprise'
# UTF-16 code units — avoids .ps1 encoding issues on Windows PowerShell 5.1
$personalDirZh = Join-Path $outRoot ($([char]0x4E2A) + [char]0x4EBA + [char]0x7248)
$enterpriseDirZh = Join-Path $outRoot ($([char]0x4F01) + [char]0x4E1A + [char]0x7248)

foreach ($d in @($personalDir, $enterpriseDir, $personalDirZh, $enterpriseDirZh)) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}

$winPersonal = Join-Path $Root "release\xcagi-v$Version\personal\XCAGI-Personal-Setup-$Version-x64.exe"
$winEnterprise = Join-Path $Root "release\xcagi-v$Version\enterprise\XCAGI-Enterprise-Setup-$Version-x64.exe"

$androidRoot = Join-Path $Root 'mobile-android'
$iconScript = Join-Path $PSScriptRoot 'generate-android-icons.py'
if (Test-Path $iconScript) {
  python $iconScript
  if ($LASTEXITCODE -ne 0) { throw 'generate-android-icons.py failed' }
}

if ($BuildAndroidRelease) {
  $signedScript = Join-Path $PSScriptRoot 'build-android-release-signed.ps1'
  $propsFile = Join-Path $androidRoot 'keystore.properties'
  if ((Test-Path $propsFile) -or $env:XCAGI_ANDROID_KEYSTORE) {
    & $signedScript
    if ($LASTEXITCODE -ne 0) { throw 'build-android-release-signed.ps1 failed' }
  } else {
    Write-Warning '未找到 keystore.properties，Release 将使用 debug 签名。请先运行 new-android-release-keystore.ps1'
    Push-Location $androidRoot
    & .\gradlew.bat assemblePersonalRelease assembleEnterpriseRelease --no-daemon
    Pop-Location
  }
}

$apkPersonalCandidates = @(
  (Join-Path $androidRoot 'app\build\outputs\apk\personal\release\app-personal-release.apk'),
  (Join-Path $androidRoot 'app\build\outputs\apk\personal\debug\app-personal-debug.apk')
)
$apkEnterpriseCandidates = @(
  (Join-Path $androidRoot 'app\build\outputs\apk\enterprise\release\app-enterprise-release.apk'),
  (Join-Path $androidRoot 'app\build\outputs\apk\enterprise\debug\app-enterprise-debug.apk')
)

function Resolve-FirstFile([string[]]$paths) {
  foreach ($p in $paths) {
    if (Test-Path $p) { return (Resolve-Path $p).Path }
  }
  return $null
}

function Copy-IfExists([string]$src, [string]$destDir, [string]$destName) {
  if (-not $src -or -not (Test-Path $src)) { return $false }
  Copy-Item -LiteralPath $src -Destination (Join-Path $destDir $destName) -Force
  return $true
}

$apkPersonal = Resolve-FirstFile $apkPersonalCandidates
$apkEnterprise = Resolve-FirstFile $apkEnterpriseCandidates

$winPersonalName = "XCAGI-Personal-Windows-$Version-x64.exe"
$winEnterpriseName = "XCAGI-Enterprise-Windows-$Version-x64.exe"
$apkPersonalName = "XCAGI-Personal-Android-$AndroidVersion.apk"
$apkEnterpriseName = "XCAGI-Enterprise-Android-$AndroidVersion.apk"

function Remove-OldAndroidApks([string]$dir, [string]$keepName) {
  Get-ChildItem -LiteralPath $dir -Filter 'XCAGI-*-Android-*.apk' -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne $keepName } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
}

function Stage-SkuPair(
  [string]$srcWin,
  [string]$srcApk,
  [string]$enDir,
  [string]$zhDir,
  [string]$winName,
  [string]$apkName,
  [ref]$okList
) {
  if (Copy-IfExists $srcWin $enDir $winName) { $okList.Value += 'Windows' }
  if (Copy-IfExists $srcWin $zhDir $winName) { }
  if (Copy-IfExists $srcApk $enDir $apkName) {
    $okList.Value += 'Android'
    Remove-OldAndroidApks $enDir $apkName
  }
  if (Copy-IfExists $srcApk $zhDir $apkName) {
    Remove-OldAndroidApks $zhDir $apkName
  }
}

$okP = [System.Collections.Generic.List[string]]::new()
$okE = [System.Collections.Generic.List[string]]::new()
Stage-SkuPair $winPersonal $apkPersonal $personalDir $personalDirZh $winPersonalName $apkPersonalName ([ref]$okP)
Stage-SkuPair $winEnterprise $apkEnterprise $enterpriseDir $enterpriseDirZh $winEnterpriseName $apkEnterpriseName ([ref]$okE)

$readmePersonal = @"
XCAGI 个人版 (Personal) v$Version

  本目录仅含个人版安装包，与企业版不可混用。
  Windows: $winPersonalName
  Android: $apkPersonalName
  包名: com.xiuci.xcagi.mobile.personal
"@
$readmeEnterprise = @"
XCAGI 企业版 (Enterprise) v$Version

  本目录仅含企业版安装包，与个人版不可混用。
  Windows: $winEnterpriseName
  Android: $apkEnterpriseName
  包名: com.xiuci.xcagi.mobile.enterprise
"@
foreach ($pair in @(
    @{ En = $personalDir; Zh = $personalDirZh; Text = $readmePersonal },
    @{ En = $enterpriseDir; Zh = $enterpriseDirZh; Text = $readmeEnterprise }
  )) {
  Set-Content -Path (Join-Path $pair.En 'README.txt') -Value $pair.Text -Encoding UTF8
  Set-Content -Path (Join-Path $pair.Zh 'README.txt') -Value $pair.Text -Encoding UTF8
}

Write-Host "Done: $outRoot"
Write-Host "  personal / 个人版   -> $($okP -join ', ')"
Write-Host "  enterprise / 企业版 -> $($okE -join ', ')"
