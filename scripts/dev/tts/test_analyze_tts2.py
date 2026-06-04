import asyncio
import edge_tts


async def analyze_audio_full():
    text = "你好呀！我是您的智能助手，XCAGI测试"
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")

    print(f"原始文本: {text}")
    print(f"文本长度: {len(text)}")
    print("\n=== 所有事件 ===")

    event_types = {}
    total_audio = 0

    async for chunk in communicate.stream():
        event_type = chunk.get("type", "unknown")
        event_types[event_type] = event_types.get(event_type, 0) + 1

        if event_type == "audio":
            data = chunk.get("data")
            if data:
                total_audio += len(data)
        elif event_type in ["WordBoundary", "SentenceBoundary"]:
            word = chunk.get("text", "")
            offset = chunk.get("offset", 0) / 10000000
            duration = chunk.get("duration", 0) / 10000000
            print(f"  [{event_type}] '{word}' ({offset:.2f}s - {offset+duration:.2f}s)")

    print(f"\n=== 事件统计 ===")
    for etype, count in event_types.items():
        print(f"  {etype}: {count}")
    print(f"\n总音频大小: {total_audio} bytes")


asyncio.run(analyze_audio_full())
