import json, base64, urllib.request

data = json.dumps({"text": "您好", "voice": "zh-CN-XiaoxiaoNeural", "lang": "zh"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/tts/synthesize",
    data=data,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
audio_b64 = result.get("data", {}).get("audio_base64", "")
print("Voice:", result.get("data", {}).get("voice"))
print("Audio b64 len:", len(audio_b64))
if audio_b64.startswith("data:audio/mpeg;base64,"):
    audio_data = base64.b64decode(audio_b64.split(",", 1)[1])
    with open("e:/FHD/tts_test_output.mp3", "wb") as f:
        f.write(audio_data)
    print(f"Saved {len(audio_data)} bytes to tts_test_output.mp3")
