"""
OCR 基础设施实现

负责 OCR 服务的具体实现
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class OCRPort(ABC):
    """OCR 端口接口"""

    @abstractmethod
    def recognize_text(self, image_path: str) -> Dict[str, Any]:
        """识别文字"""
        pass

    @abstractmethod
    def recognize_text_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """从字节数据识别文字"""
        pass


class OCRAdapter(OCRPort):
    """OCR 适配器"""

    def __init__(self):
        pass

    def recognize_text(self, image_path: str) -> Dict[str, Any]:
        """识别文字"""
        return {
            "success": True,
            "text": "",
            "confidence": 0.0
        }

    def recognize_text_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """从字节数据识别文字"""
        return {
            "success": True,
            "text": "",
            "confidence": 0.0
        }


def get_ocr_adapter() -> OCRPort:
    """获取 OCR 适配器"""
    return OCRAdapter()
