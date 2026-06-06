# 生产上架：局域网授权 AI 员工 + bridge 侧栏解耦
# 用法: powershell -File scripts/deploy/deploy-lan-gate-production.ps1

$ErrorActionPreference = "Stop"
$HostAddr = "119.27.178.147"
$SshOpts = @("-o", "StrictHostKeyChecking=no")
$Remote = "root@${HostAddr}"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$RemoteRoot = "/opt/fhd-full"
$RemoteMods = "$RemoteRoot/XCAGI/mods"

Write-Host "==> 同步 Mod 与后端到 $HostAddr"
& scp @SshOpts -r (Join-Path $Repo "mods/lan-gate-ai-employee") "${Remote}:${RemoteMods}/"
& scp @SshOpts (Join-Path $Repo "mods/xcagi-lan-license-bridge/manifest.json") "${Remote}:${RemoteMods}/xcagi-lan-license-bridge/"
& scp @SshOpts (Join-Path $Repo "mods/xcagi-lan-license-bridge/frontend/routes.js") "${Remote}:${RemoteMods}/xcagi-lan-license-bridge/frontend/"
& scp @SshOpts (Join-Path $Repo "app/mod_sdk/aux_employee_store.py") "${Remote}:${RemoteRoot}/app/mod_sdk/"
& scp @SshOpts (Join-Path $Repo "scripts/deploy/patch_mod_store_aux.py") "${Remote}:/tmp/patch_mod_store_aux.py"
& ssh @SshOpts $Remote "python3 /tmp/patch_mod_store_aux.py"

Write-Host "==> 构建前端"
Push-Location (Join-Path $Repo "frontend")
if (-not (Test-Path "node_modules")) { npm ci }
npm run build
Pop-Location

Write-Host "==> 同步 frontend/dist"
& scp @SshOpts -r (Join-Path $Repo "frontend/dist") "${Remote}:${RemoteRoot}/frontend/"

Write-Host "==> 重启 fhd-full"
& ssh @SshOpts $Remote "systemctl restart fhd-full.service; sleep 2; systemctl is-active fhd-full.service"

Write-Host "==> 完成。扩展市场 -> AI 员工 应出现「局域网授权 AI 员工」"
