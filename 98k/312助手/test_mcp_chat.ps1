$body = @{
    message = "hello"
    use_tools = $false
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://127.0.0.1:5001/chat" -Method POST -Body $body -ContentType "application/json"

$response.Content
