<#
.SYNOPSIS
  Build signed personal + enterprise Release APKs (requires keystore.properties or env).

.EXAMPLE
  powershell -File scripts/package/build-android-release-signed.ps1
  powershell -File scripts/package/build-android-release-signed.ps1 -Stage -Version 8.0.0 -AndroidVersion 1.3.0
#>
param(
  [switch]$Stage,
  [string]$Version = '8.0.0',
  [string]$AndroidVersion = '1.3.0'
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$MobileRoot = Join-Path $Root 'mobile-android'
$PropsPath = Join-Path $MobileRoot 'keystore.properties'

function Load-KeystoreEnv {
  if ($env:XCAGI_ANDROID_KEYSTORE -and (Test-Path $env:XCAGI_ANDROID_KEYSTORE)) {
    return
  }
  if (-not (Test-Path $PropsPath)) {
    throw @"
未配置 Release 签名。
  1) 运行: powershell -File scripts/package/new-android-release-keystore.ps1
  或 2) 复制 mobile-android/keystore.properties.example → keystore.properties
  或 3) 设置环境变量 XCAGI_ANDROID_KEYSTORE / XCAGI_ANDROID_KEYSTORE_PASSWORD / XCAGI_ANDROID_KEY_ALIAS / XCAGI_ANDROID_KEY_PASSWORD
"@
  }
  $lines = Get-Content -LiteralPath $PropsPath | Where-Object { $_ -match '^\s*[^#]' }
  $map = @{}
  foreach ($line in $lines) {
    if ($line -match '^\s*([^=]+)=(.*)$') {
      $map[$Matches[1].Trim()] = $Matches[2].Trim()
    }
  }
  $storeRel = $map['storeFile']
  if (-not $storeRel) { throw 'keystore.properties 缺少 storeFile' }
  $storeAbs = Join-Path $MobileRoot $storeRel
  if (-not (Test-Path $storeAbs)) { throw "找不到密钥库: $storeAbs" }

  $env:XCAGI_ANDROID_KEYSTORE = $storeAbs
  $env:XCAGI_ANDROID_KEYSTORE_PASSWORD = $map['storePassword']
  $env:XCAGI_ANDROID_KEY_ALIAS = $map['keyAlias']
  $env:XCAGI_ANDROID_KEY_PASSWORD = if ($map['keyPassword']) { $map['keyPassword'] } else { $map['storePassword'] }
  $env:XCAGI_REQUIRE_RELEASE_SIGNING = '1'
}

Load-KeystoreEnv

Push-Location $MobileRoot
try {
  & .\gradlew.bat assemblePersonalRelease assembleEnterpriseRelease --no-daemon
  if ($LASTEXITCODE -ne 0) { throw 'Gradle release build failed' }
} finally {
  Pop-Location
}

function Find-Apksigner {
  $sdk = $env:ANDROID_HOME
  if (-not $sdk) { $sdk = $env:ANDROID_SDK_ROOT }
  if ($sdk) {
    $buildTools = Join-Path $sdk 'build-tools'
    if (Test-Path $buildTools) {
      $latest = Get-ChildItem $buildTools -Directory | Sort-Object Name -Descending | Select-Object -First 1
      $p = Join-Path $latest.FullName 'apksigner.bat'
      if (Test-Path $p) { return $p }
    }
  }
  return $null
}

$apks = @(
  (Join-Path $MobileRoot 'app\build\outputs\apk\personal\release\app-personal-release.apk')
  (Join-Path $MobileRoot 'app\build\outputs\apk\enterprise\release\app-enterprise-release.apk')
)
$signer = Find-Apksigner
foreach ($apk in $apks) {
  if (-not (Test-Path $apk)) { throw "未找到 APK: $apk" }
  if ($signer) {
    Write-Host "验证签名: $apk"
    & $signer verify --verbose $apk
    if ($LASTEXITCODE -ne 0) { throw "apksigner verify failed: $apk" }
  } else {
    Write-Host "跳过 apksigner（未设置 ANDROID_HOME）: $apk"
  }
}

Write-Host ''
Write-Host '已签名 Release APK:'
foreach ($apk in $apks) { Write-Host "  $apk" }

if ($Stage) {
  & (Join-Path $PSScriptRoot 'stage-sku-download-folders.ps1') -Version $Version -AndroidVersion $AndroidVersion
}
