# Desktop SQLite deliverable smoke (repo root)
# Uses TestClient + configure_desktop_environment (same contract as live --desktop, without multi-minute uvicorn cold start).
param(
    [switch]$UseLiveServer,
    [int]$Port = 5099
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

$py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    $py = 'python'
}

if ($UseLiveServer) {
    $Tmp = Join-Path $env:TEMP ("xcagi-desktop-smoke-{0}" -f [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $Tmp -Force | Out-Null
    $Xcagi = Join-Path $Root 'XCAGI'
    $lanOff = Join-Path $Tmp 'lan_settings.json'
    [System.IO.File]::WriteAllText($lanOff, '{"enabled":false}', [System.Text.UTF8Encoding]::new($false))
    $env:LAN_GUARD_ENABLED = '0'
    $env:LAN_SETTINGS_FILE = $lanOff
    $env:XCAGI_DESKTOP_MODE = '1'
    $env:XCAGI_PRODUCT_SKU = 'enterprise'
    $env:XCAGI_MOD_ISOLATED_DATABASES = '0'
    $env:XCAGI_FORCE_SYNC_TASKS = '0'
    $env:XCAGI_DATA_DIR = $Tmp
    $proc = $null
    try {
        $proc = Start-Process -FilePath $py -ArgumentList @(
            'run_fastapi.py', '--desktop', '--headless', '--host', '127.0.0.1', '--port', "$Port", '--data-dir', $Tmp
        ) -WorkingDirectory $Xcagi -PassThru -WindowStyle Hidden
        $healthUrl = "http://127.0.0.1:$Port/api/health"
        $ready = $false
        for ($i = 1; $i -le 300; $i++) {
            try {
                $h = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 5
                if ($h.StatusCode -eq 200) { $ready = $true; break }
            } catch {
                if ($proc.HasExited) { throw "Backend exited (code=$($proc.ExitCode))" }
                Start-Sleep -Seconds 1
            }
        }
        if (-not $ready) { throw "Timed out: $healthUrl" }
        $status = Invoke-RestMethod "http://127.0.0.1:$Port/api/desktop/status" -TimeoutSec 30
        if ($status.storageMode -ne 'local_sqlite') { throw "storageMode=$($status.storageMode)" }
        if ($status.database -notmatch 'xcagi\.db') { throw "database=$($status.database)" }
    }
    finally {
        if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
    }
    Write-Host '[OK] desktop deliverable smoke (live server)' -ForegroundColor Green
    exit 0
}

$pyCode = @"
import json
import os
import tempfile
from pathlib import Path

from app.desktop_runtime import configure_desktop_environment
from app.fastapi_app import create_fastapi_app
from app.security.lan_settings_store import LanSettingsOverride
from fastapi.testclient import TestClient

tmpdir = tempfile.mkdtemp(prefix='xcagi-desktop-smoke-')
os.environ['LAN_GUARD_ENABLED'] = '0'
os.environ['XCAGI_DESKTOP_MODE'] = '1'
configure_desktop_environment(tmpdir)

import app.security.lan_settings_store as lan_store
lan_store.load_overrides = lambda: LanSettingsOverride(enabled=False)
from app.security.lan_config import reset_lan_config_cache
reset_lan_config_cache()

client = TestClient(create_fastapi_app())
health = client.get('/api/health')
assert health.status_code == 200, health.text
status = client.get('/api/desktop/status')
assert status.status_code == 200, status.text
payload = status.json()
assert payload.get('desktopMode') is True
assert payload.get('storageMode') == 'local_sqlite'
assert 'xcagi.db' in (payload.get('database') or '')
profile_path = Path(tmpdir) / 'config' / 'database.json'
assert profile_path.is_file(), profile_path
profile = json.loads(profile_path.read_text(encoding='utf-8'))
assert profile.get('mode') == 'local'
print('desktop-deliverable-smoke-ok', payload.get('database'))
"@

python -c $pyCode
if ($LASTEXITCODE -ne 0) { throw 'Desktop SQLite deliverable smoke failed' }
Write-Host '[OK] desktop deliverable smoke' -ForegroundColor Green
