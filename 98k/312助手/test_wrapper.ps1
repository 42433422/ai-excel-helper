$body = @{
    model = "claude-opus-4-6"
    max_tokens = 10
    messages = @(
        @{role = "user"; content = "hi"}
    )
} | ConvertTo-Json -Depth 3

$response = Invoke-WebRequest -Uri "http://127.0.0.1:5002/v1/messages" -Method POST -Body $body -ContentType "application/json" -Headers @{Authorization = "Bearer sk-test"}

$response.Content
