<#
.SYNOPSIS
  Generate XCAGI Android release keystore and local keystore.properties (gitignored).

.EXAMPLE
  powershell -File scripts/package/new-android-release-keystore.ps1
#>
param(
  [string]$Alias = 'xcagi_release',
  [int]$ValidityDays = 10000
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$MobileRoot = Join-Path $Root 'mobile-android'
$SigningDir = Join-Path $MobileRoot 'signing'
$KeystorePath = Join-Path $SigningDir 'xcagi-release.jks'
$PropsPath = Join-Path $MobileRoot 'keystore.properties'

function Find-Keytool {
  if ($env:JAVA_HOME) {
    $p = Join-Path $env:JAVA_HOME 'bin\keytool.exe'
    if (Test-Path $p) { return $p }
  }
  $cmd = Get-Command keytool -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw '找不到 keytool。请安装 JDK 17+ 并设置 JAVA_HOME，或将 keytool 加入 PATH。'
}

New-Item -ItemType Directory -Force -Path $SigningDir | Out-Null

if (Test-Path $KeystorePath) {
  Write-Host "已存在: $KeystorePath"
  $overwrite = Read-Host '覆盖并重新生成? (y/N)'
  if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
    Write-Host '已取消。'
    exit 0
  }
  Remove-Item -LiteralPath $KeystorePath -Force
}

Write-Host '请设置密钥库密码（至少 6 位，用于 store 与 key，请妥善备份）。'
$storePass = Read-Host '密钥库密码' -AsSecureString
$storePlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($storePass),
)
if ([string]::IsNullOrWhiteSpace($storePlain) -or $storePlain.Length -lt 6) {
  throw '密码太短或为空。'
}

$keytool = Find-Keytool
$dname = 'CN=成都修茈科技有限公司, OU=Mobile, O=Xiuci, L=Chengdu, ST=Sichuan, C=CN'

& $keytool -genkeypair -v `
  -storetype JKS `
  -keystore $KeystorePath `
  -alias $Alias `
  -keyalg RSA `
  -keysize 2048 `
  -validity $ValidityDays `
  -storepass $storePlain `
  -keypass $storePlain `
  -dname $dname

if ($LASTEXITCODE -ne 0) { throw 'keytool 失败' }

$relStore = 'signing/xcagi-release.jks'
$content = @"
# 自动生成 — 勿提交 Git
storeFile=$relStore
storePassword=$storePlain
keyAlias=$Alias
keyPassword=$storePlain
"@
Set-Content -LiteralPath $PropsPath -Value $content -Encoding UTF8

Write-Host ''
Write-Host '完成:'
Write-Host "  密钥库: $KeystorePath"
Write-Host "  配置:   $PropsPath"
Write-Host ''
Write-Host '下一步:'
Write-Host '  powershell -File scripts/package/build-android-release-signed.ps1'
Write-Host ''
Write-Host '请将 .jks 与密码备份到公司密钥库；丢失后无法为同一包名发布更新。'
