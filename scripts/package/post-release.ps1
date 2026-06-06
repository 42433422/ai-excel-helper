param(
  [string]$Version = '8.0.0',
  [switch]$Upload,
  [switch]$DryRunUpload
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'pre-release-security.ps1') -Phase post -Version $Version

if ($Upload) {
  $uploadArgs = @('-File', (Join-Path $PSScriptRoot 'upload-release-skus.ps1'), '-Version', $Version)
  if ($DryRunUpload) { $uploadArgs += '-DryRun' }
  powershell -ExecutionPolicy Bypass @uploadArgs
}

Write-Host 'Post-release steps finished.'
