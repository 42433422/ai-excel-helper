$body = @{
    model = "deepseek-chat"
    max_tokens = 10
    messages = @(
        @{role = "user"; content = "hi"}
    )
} | ConvertTo-Json -Depth 3

$response = Invoke-WebRequest -Uri "https://api.deepseek.com/v1/chat/completions" -Method POST -Body $body -ContentType "application/json" -Headers @{Authorization = "Bearer sk-5670fc1d73c74f21b4948d7496b7bf16"}

$response.Content
