#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信聊天记录读取器 - 完整版
- 颜色判断发送者
- 过滤系统提示词
- 时间戳向下关联
"""

import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class ChatMessage:
    content: str = ""
    timestamp: str = ""
    is_self: bool = False


class FinalReader:
    """最终版读取器"""

    def __init__(self):
        import easyocr
        self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        self.timestamp_pattern = re.compile(r'^星期[一二三四五六日天]?\d{1,2}:\d{2}$')
        self.system_keywords = ['已添加了', '打招呼', '以上是', '验证消息']

    def read(self, window_info=None) -> List[ChatMessage]:
        from PIL import ImageGrab
        import numpy as np
        from wechat_window import WeChatWindowDetector

        detector = WeChatWindowDetector()

        if window_info is None:
            window_info = detector.find_wechat_window()

        if window_info is None:
            return []

        chat_area = detector.get_chat_area(window_info)
        screenshot = ImageGrab.grab(bbox=chat_area)
        img_array = np.array(screenshot)

        return self._parse_chat_image(img_array)

    def _parse_chat_image(self, img_array) -> List[ChatMessage]:
        h, w = img_array.shape[:2]

        chat_region = self._extract_chat_region(img_array)
        if chat_region is None:
            return []

        items = self._ocr_with_color(chat_region, h)
        if not items:
            return []

        messages = self._parse_items(items)
        return messages

    def _extract_chat_region(self, img_array):
        h, w = img_array.shape[:2]

        for x in range(w):
            pixel = img_array[h // 2, x]
            if pixel[0] < 30 and pixel[1] < 30 and pixel[2] < 30:
                return img_array[:, x:, :]

        return img_array

    def _ocr_with_color(self, chat_region, full_h) -> List[Dict]:
        results = self.reader.readtext(chat_region, detail=1, paragraph=False)

        items = []
        for bbox, text, conf in results:
            text = text.strip()
            if not text:
                continue

            x1, y1 = bbox[0]
            x2, y2 = bbox[2]

            region = chat_region[
                max(0, int(y1)):min(int(y2) + 5, full_h),
                max(0, int(x1)):min(int(x2) + 5, chat_region.shape[1]),
                :
            ]

            avg_color = region.mean(axis=(0, 1))
            green_diff = avg_color[1] - avg_color[0]

            items.append({
                'text': text,
                'conf': conf,
                'y1': int(y1),
                'y2': int(y2),
                'is_self': green_diff > 5
            })

        items.sort(key=lambda x: x['y1'])
        return items

    def _parse_items(self, items: List[Dict]) -> List[ChatMessage]:
        """解析所有项目"""
        if not items:
            return []

        messages = []
        i = 0
        n = len(items)
        pending_timestamp = None

        while i < n:
            item = items[i]

            text = item['text']
            is_timestamp = self.timestamp_pattern.match(text)
            is_system = any(kw in text for kw in self.system_keywords)

            if is_system:
                i += 1
                continue

            if is_timestamp:
                pending_timestamp = text
                i += 1
                continue

            msg = ChatMessage()
            msg.content = text
            msg.timestamp = pending_timestamp or ""
            msg.is_self = item['is_self']
            pending_timestamp = None

            if msg.content.strip():
                messages.append(msg)

            i += 1

        return messages


def main():
    print("=== 微信聊天记录读取器 ===\n")

    reader = FinalReader()
    messages = reader.read()

    print(f"读取到 {len(messages)} 条消息:\n")

    for i, msg in enumerate(messages, 1):
        sender = "[自己]" if msg.is_self else "[对方]"
        timestamp = f" {msg.timestamp}" if msg.timestamp else ""
        print(f"{i}. {sender}{timestamp}: {msg.content}")

    return messages


if __name__ == "__main__":
    main()
