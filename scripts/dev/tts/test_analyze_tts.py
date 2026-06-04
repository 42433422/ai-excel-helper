import asyncio
import edge_tts


async def analyze_audio():
    text = "你好呀！我是您的智能助手"
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")

    print(f"原始文本: {text}")
    print("\n=== WordBoundary 事件 ===")

    word_count = 0
    char_count = 0

    async for chunk in communicate.stream():
        if chunk.get("type") == "WordBoundary":
            word = chunk.get("text", "")
            offset = chunk.get("offset", 0) / 10000000  # 转换为秒
            duration = chunk.get("duration", 0) / 10000000
            word_count += 1
            char_count += len(word)
            print(f"  [{offset:.2f}s-{offset+duration:.2f}s] '{word}' ({len(word)}字符)")
        elif chunk.get("type") == "audio":
            audio_len = len(chunk.get("data", b""))

    print(f"\n总单词数: {word_count}")
    print(f"总字符数: {char_count}")
    print(f"原始文本长度: {len(text)}")


asyncio.run(analyze_audio())
