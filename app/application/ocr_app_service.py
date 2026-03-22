"""
OCR 应用服务

负责 OCR 文字识别相关的用例编排
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from app.services import OCRService


class OCRApplicationService:
    """OCR 应用服务 - 负责 OCR 相关的用例编排"""

    def __init__(
        self,
        ocr_service: Optional["OCRService"] = None,
    ):
        if ocr_service is None:
            from app.services import get_ocr_service
            ocr_service = get_ocr_service()
        self._ocr_service = ocr_service

    def recognize_text(self, image_path: str) -> Dict[str, Any]:
        """
        识别图片文字用例

        Args:
            image_path: 图片路径

        Returns:
            识别结果
        """
        return self._ocr_service.recognize_text(image_path)

    def recognize_text_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        从字节数据识别文字用例

        Args:
            image_bytes: 图片字节数据

        Returns:
            识别结果
        """
        return self._ocr_service.recognize_text_from_bytes(image_bytes)

    def recognize_trademark(self, image_path: str) -> Dict[str, Any]:
        """
        识别商标用例

        Args:
            image_path: 图片路径

        Returns:
            商标识别结果
        """
        return self._ocr_service.recognize_trademark(image_path)

    def recognize_product(self, image_path: str) -> Dict[str, Any]:
        """
        识别产品信息用例

        Args:
            image_path: 图片路径

        Returns:
            产品识别结果
        """
        return self._ocr_service.recognize_product(image_path)

    def batch_recognize(self, image_paths: list) -> Dict[str, Any]:
        """
        批量识别用例

        Args:
            image_paths: 图片路径列表

        Returns:
            批量识别结果
        """
        results = []
        for image_path in image_paths:
            result = self._ocr_service.recognize_text(image_path)
            results.append({
                "image_path": image_path,
                "result": result
            })

        success_count = sum(1 for r in results if r["result"].get("success"))
        return {
            "success": True,
            "data": results,
            "total": len(results),
            "success_count": success_count,
            "fail_count": len(results) - success_count
        }


_ocr_app_service: Optional[OCRApplicationService] = None


def get_ocr_app_service() -> OCRApplicationService:
    """获取 OCR 应用服务单例 (别名)"""
    return get_ocr_application_service()


def get_ocr_application_service() -> OCRApplicationService:
    """获取 OCR 应用服务单例"""
    global _ocr_app_service
    if _ocr_app_service is None:
        _ocr_app_service = OCRApplicationService()
    return _ocr_app_service


def init_ocr_app_service(
    ocr_service: "OCRService",
) -> OCRApplicationService:
    """初始化 OCR 应用服务 (用于依赖注入) (别名)"""
    return init_ocr_application_service(ocr_service)


def init_ocr_application_service(
    ocr_service: "OCRService",
) -> OCRApplicationService:
    """初始化 OCR 应用服务 (用于依赖注入)"""
    global _ocr_app_service
    _ocr_app_service = OCRApplicationService(
        ocr_service=ocr_service
    )
    return _ocr_app_service
