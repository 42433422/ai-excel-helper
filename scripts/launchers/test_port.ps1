# Probe TCP connectivity to a host:port (default backend dev port).
# Replaces duplicate XCAGI/test_port*.ps1 variants.
param(
    [string]$TargetHost = "127.0.0.1",
    [int]$Port = 8000
)

$client = New-Object System.Net.Sockets.TcpClient
try {
    $client.Connect($TargetHost, $Port)
    Write-Host "Connected to ${TargetHost}:${Port}"
} catch {
    Write-Host "Failed ${TargetHost}:${Port} - $($_.Exception.Message)"
} finally {
    $client.Dispose()
}
