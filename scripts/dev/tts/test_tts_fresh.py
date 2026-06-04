import json, base64, urllib.request, time

# 清除缓存影响 - 添加时间戳
payload = {
    "text": f"你好呀！我是您的智能助手_{time.time()}",
    "lang": "zh",
    "voice": "zh-CN-XiaoxiaoNeural",
}

print(f"发送文本: {payload['text']}")

data = json.dumps(payload).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/tts/synthesize",
    data=data,
    headers={"Content-Type": "application/json"},
)

resp = urllib.request.urlopen(req)
result = json.loads(resp.read())

print(f"Response voice: {result.get('data',{}).get('voice')}")
audio_b64 = result.get("data", {}).get("audio_base64", "")
print(f"Audio b64 length: {len(audio_b64)}")

if audio_b64.startswith("data:audio/mpeg;base64,"):
    audio_data = base64.b64decode(audio_b64.split(",", 1)[1])
    print(f"Audio data size: {len(audio_data)} bytes")

    with open("e:/FHD/tts_fresh_test.mp3", "wb") as f:
        f.write(audio_data)
    print("Saved to tts_fresh_test.mp3")
