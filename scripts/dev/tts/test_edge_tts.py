import asyncio
import edge_tts
import base64


async def test_full():
    texts = ["你好", "你好呀！我是您的智能助手", "XCAGI", "你好 XCAGI 测试"]

    for text in texts:
        print(f"\n=== 测试文本: {text} ===")
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")

        # 获取所有事件
        events = []
        audio_chunks = []
        async for chunk in communicate.stream():
            events.append(chunk["type"])
            if chunk["type"] == "audio":
                data = chunk.get("data")
                if data:
                    audio_chunks.append(data)
            elif chunk.get("type") in ["WordBoundary", "SentenceBoundary"]:
                print(f"  边界: {chunk.get('text', '')}")

        audio_data = b"".join(audio_chunks)
        b64 = base64.b64encode(audio_data).decode()

        print(f"  音频大小: {len(audio_data)} bytes")
        print(f"  Base64前50: {b64[:50]}")

        # 保存文件
        filename = f"e:/FHD/tts_test_{len(text)}.mp3"
        with open(filename, "wb") as f:
            f.write(audio_data)
        print(f"  已保存: {filename}")


asyncio.run(test_full())
