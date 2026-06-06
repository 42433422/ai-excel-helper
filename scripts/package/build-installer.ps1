param(
  [string]$Version = "8.0.0",
  [switch]$SkipBackend,
  [Parameter(Mandatory = $true)]
  [ValidateSet('personal', 'enterprise')]
  [string]$ProductSku,
  [switch]$SkipUiInstaller
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$Version = $Version.TrimStart("v", "V")

$skuLabels = @{
  personal   = 'Personal'
  enterprise = 'Enterprise'
}
$skuAppIds = @{
  personal   = 'com.xcagi.desktop.personal'
  enterprise = 'com.xcagi.desktop.enterprise'
}
$skuUpdateUrls = @{
  personal   = 'https://update.xcagi.com/releases/stable/personal/'
  enterprise = 'https://update.xcagi.com/releases/stable/enterprise/'
}

$label = $skuLabels[$ProductSku]
$releaseRoot = Join-Path $Root "release\xcagi-v$Version"
$outDir = Join-Path $releaseRoot $ProductSku
$finalSetupName = "XCAGI-$label-Setup-$Version-x64.exe"
$finalSetupPath = Join-Path $outDir $finalSetupName
$licenseSrc = Join-Path $Root "tools\XcagiInstaller\Assets\LICENSE.zh-CN.txt"
if (-not (Test-Path $licenseSrc)) {
  $licenseSrc = Join-Path $Root "LICENSE"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

if (-not $SkipBackend) {
  & "$PSScriptRoot\build-backend.ps1" -Version $Version -ProductSku $ProductSku
} else {
  python -m pip install "Pillow>=10.2.0" -q
}

$skuJson = Join-Path $Root "build\product-sku.json"
$desktopSku = Join-Path $Root "desktop\resources\product-sku.json"
if (Test-Path $skuJson) {
  Copy-Item $skuJson $desktopSku -Force
} else {
  @{ sku = $ProductSku; schema_version = 1 } | ConvertTo-Json | Set-Content $desktopSku -Encoding UTF8
}

& "$PSScriptRoot\create-installer-assets.ps1"

Push-Location (Join-Path $Root "desktop")
if (-not (Test-Path "node_modules")) {
  npm install
}
npm version $Version --no-git-tag-version
$ebAppId = $skuAppIds[$ProductSku]
$ebPublishUrl = $skuUpdateUrls[$ProductSku]
$ebArtifact = "XCAGI-$label-Setup-`${version}-`${arch}.`${ext}"
npx electron-builder --win nsis zip --x64 `
  "--config.directories.output=../release/xcagi-v$Version/$ProductSku" `
  "--config.appId=$ebAppId" `
  "--config.publish.url=$ebPublishUrl" `
  "--config.nsis.artifactName=$ebArtifact" `
  "--config.extraMetadata.productSku=$ProductSku"
Pop-Location

$nsisExe = Get-ChildItem $outDir -Filter "XCAGI-$label-Setup-*.exe" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $nsisExe) {
  $nsisExe = Get-ChildItem $outDir -Filter "XCAGI-*-Setup-*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

if (-not $SkipUiInstaller) {
  if (-not $nsisExe) {
    throw "NSIS artifact not found in $outDir; cannot build single-file installer."
  }

  $stagingNsis = Join-Path $outDir 'nsis-payload.tmp.exe'
  Copy-Item $nsisExe.FullName $stagingNsis -Force

  $uiProj = Join-Path $Root "tools\XcagiInstaller\XcagiInstaller.csproj"
  $uiOut = Join-Path $outDir "ui-build"
  New-Item -ItemType Directory -Force -Path $uiOut | Out-Null

  $publishArgs = @(
    "publish", $uiProj,
    "-c", "Release",
    "-r", "win-x64",
    "--self-contained", "true",
    "-p:PublishSingleFile=true",
    "-p:IncludeNativeLibrariesForSelfExtract=true",
    "-p:EnableCompressionInSingleFile=true",
    "-p:Version=$Version",
    "-p:SetupPayloadPath=$stagingNsis",
    "-o", $uiOut
  )
  if (Test-Path $licenseSrc) {
    $publishArgs += "-p:LicenseFilePath=$licenseSrc"
  }
  & dotnet @publishArgs

  $uiExe = Get-ChildItem $uiOut -Filter "XcagiInstaller.exe" | Select-Object -First 1
  if (-not $uiExe) {
    throw "WPF installer publish failed."
  }

  if (Test-Path $finalSetupPath) {
    Remove-Item $finalSetupPath -Force
  }
  Move-Item $uiExe.FullName $finalSetupPath -Force
  Remove-Item $uiOut -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item $stagingNsis -Force -ErrorAction SilentlyContinue
  if ($nsisExe -and (Test-Path $nsisExe.FullName) -and $nsisExe.FullName -ne $finalSetupPath) {
    Remove-Item $nsisExe.FullName -Force
  }

  $legacyPayload = Join-Path $outDir "_payload"
  if (Test-Path $legacyPayload) {
    Remove-Item $legacyPayload -Recurse -Force
  }
  Get-ChildItem $outDir -Filter "XCAGI-*-*.exe" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*安装程序*' } |
    Remove-Item -Force -ErrorAction SilentlyContinue

  node (Join-Path $Root "scripts\package\generate-update-metadata.mjs") $finalSetupPath $Version win
} elseif ($nsisExe) {
  node (Join-Path $Root "scripts\package\generate-update-metadata.mjs") $nsisExe.FullName $Version win
}

$dlProj = Join-Path $Root "tools\XcagiDownloader\XcagiDownloader.csproj"
$dlOut = Join-Path $outDir "tools"
New-Item -ItemType Directory -Force -Path $dlOut | Out-Null
dotnet publish $dlProj -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true `
  -p:IncludeNativeLibrariesForSelfExtract=true `
  -p:EnableCompressionInSingleFile=true `
  -o $dlOut

Write-Host ""
Write-Host "Done: release\xcagi-v$Version\$ProductSku\$finalSetupName"
