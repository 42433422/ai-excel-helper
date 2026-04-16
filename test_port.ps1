$client = New-Object System.Net.Sockets.TcpClient
try {
    $client.Connect('127.0.0.1', 8000)
    Write-Host "Port 8000: Connected"
} catch {
    Write-Host "Port 8000: Failed - $($_.Exception.Message)"
}
$client.Dispose()
