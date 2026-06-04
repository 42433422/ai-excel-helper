import json, base64, urllib.request

# 模拟前端发送的完整请求
test_cases = [
    {"text": "你好呀！", "lang": "zh", "voice": "zh-CN-XiaoxiaoNeural"},
    {"text": "你好呀！我是您的智能助手", "lang": "zh", "voice": "zh-CN-XiaoxiaoNeural"},
]

for i, payload in enumerate(test_cases):
    print(f"\n=== 测试 {i+1}: {payload['text']} ===")

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/tts/synthesize",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())

        voice = result.get("data", {}).get("voice")
        audio_b64 = result.get("data", {}).get("audio_base64", "")

        print(f"  Response voice: {voice}")
        print(f"  Audio b64 length: {len(audio_b64)}")

        if audio_b64 and audio_b64.startswith("data:audio/mpeg;base64,"):
            audio_data = base64.b64decode(audio_b64.split(",", 1)[1])
            print(f"  Audio data size: {len(audio_data)} bytes")

            # 保存
            filename = f"e:/FHD/tts_api_test_{i}.mp3"
            with open(filename, "wb") as f:
                f.write(audio_data)
            print(f"  Saved to: {filename}")
    except Exception as e:
        print(f"  Error: {e}")
