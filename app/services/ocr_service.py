"""
OCR服务模块

提供图像文字识别、结构化数据提取等业务逻辑。
默认优先 PaddleOCR，与「识别模板」标签图走同一引擎；可通过环境变量切换或回退 EasyOCR/Tesseract。
"""

import logging
import os
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR识别结果"""
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    block_type: str = "text"


class OCRService:
    """OCR服务类"""

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.reader = None
        self.tesseract_available = False
        self._paddle_enabled = False
        self._init_engines()

    def _init_engines(self) -> None:
        """
        初始化识别后端。
        XCAGI_OCR_BACKEND: auto（默认）| paddle | easyocr | tesseract
        - auto: Paddle → EasyOCR → Tesseract
        - paddle: 仅 Paddle（失败则无任何引擎）
        """
        backend = os.environ.get("XCAGI_OCR_BACKEND", "auto").lower().strip() or "auto"

        if backend in ("auto", "paddle"):
            try:
                from app.services.paddle_ocr_runner import check_paddle_available, get_paddle_ocr_instance

                if check_paddle_available():
                    get_paddle_ocr_instance()
                    self._paddle_enabled = True
                    logger.info("OCR 主引擎：PaddleOCR")
            except Exception as e:
                logger.warning("PaddleOCR 初始化失败: %s", e)

        if backend == "paddle" and not self._paddle_enabled:
            logger.error("XCAGI_OCR_BACKEND=paddle 但 PaddleOCR 不可用，请安装 paddlepaddle paddleocr")

        if backend in ("auto", "easyocr") and not self._paddle_enabled:
            self._init_easyocr()

        if backend in ("auto", "tesseract") and not self._paddle_enabled and self.reader is None:
            self._init_tesseract()

        if not self._paddle_enabled and self.reader is None and not self.tesseract_available:
            self._init_tesseract()

    def _init_easyocr(self) -> None:
        try:
            import easyocr

            self.reader = easyocr.Reader(["ch_sim", "en"], gpu=self.use_gpu)
            logger.info("OCR 回退引擎：EasyOCR")
        except ImportError:
            logger.warning("EasyOCR 未安装")
            self.reader = None
        except Exception as e:
            logger.error("EasyOCR 初始化失败: %s", e)
            self.reader = None

    def _init_tesseract(self) -> None:
        """初始化Tesseract"""
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("OCR 回退引擎：Tesseract")
        except (ImportError, Exception):
            self.tesseract_available = False

    def recognize(self, image) -> str:
        """
        识别图像中的文字

        Args:
            image: PIL Image 或 numpy数组格式的图像

        Returns:
            识别出的文字
        """
        if not self._paddle_enabled and self.reader is None and not self.tesseract_available:
            logger.error("OCR引擎未初始化")
            return ""

        try:
            if hasattr(image, "convert"):
                image_array = np.array(image.convert("RGB"))
            else:
                image_array = image
                if image_array.ndim == 2:
                    image_array = np.stack([image_array] * 3, axis=-1)

            if self._paddle_enabled:
                from app.services.paddle_ocr_runner import predict_to_text_blocks

                blocks = predict_to_text_blocks(image_array)
                text = self._clean_text("\n".join(b["text"] for b in blocks if b.get("text")))
                return text

            if self.reader is not None:
                results = self.reader.readtext(image_array, detail=0)
                text = "\n".join(results)
                return self._clean_text(text)

            if self.tesseract_available:
                from PIL import Image

                pil_image = Image.fromarray(image_array)
                import pytesseract

                text = pytesseract.image_to_string(pil_image, lang="chi_sim+eng")
                return self._clean_text(text)

        except Exception as e:
            logger.error("OCR识别失败: %s", e)

        return ""

    def recognize_text_blocks(self, image) -> List[Dict[str, Any]]:
        """
        返回带坐标的文本块（标签模板网格配对等使用）。Paddle 优先，否则 EasyOCR。
        """
        if hasattr(image, "convert"):
            image_array = np.array(image.convert("RGB"))
        else:
            image_array = image
            if image_array.ndim == 2:
                image_array = np.stack([image_array] * 3, axis=-1)

        if self._paddle_enabled:
            from app.services.paddle_ocr_runner import predict_to_text_blocks

            return predict_to_text_blocks(image_array)

        if self.reader is not None:
            return self._easyocr_text_blocks(image_array)

        return []

    def _easyocr_text_blocks(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        try:
            for bbox, text, confidence in self.reader.readtext(image_array, detail=1):
                text = (text or "").strip()
                if not text:
                    continue
                xs = [float(p[0]) for p in bbox]
                ys = [float(p[1]) for p in bbox]
                left, top, right, bottom = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                blocks.append(
                    {
                        "text": text,
                        "left": left,
                        "top": top,
                        "width": right - left,
                        "height": bottom - top,
                        "conf": float(confidence) * 100.0,
                        "center": (cx, cy),
                        "y_center": cy,
                    }
                )
        except Exception as e:
            logger.error("EasyOCR 分块识别失败: %s", e)
        return blocks

    def recognize_file(self, file_path: str) -> Dict[str, Any]:
        """
        识别文件中的文字

        Args:
            file_path: 文件路径

        Returns:
            识别结果字典
        """
        try:
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}",
                    "text": ""
                }

            from PIL import Image
            image = Image.open(file_path)

            text = self.recognize(image)

            return {
                "success": True,
                "message": "识别成功",
                "text": text,
                "file_path": file_path
            }

        except Exception as e:
            logger.exception(f"识别文件失败: {e}")
            return {
                "success": False,
                "message": f"识别失败: {str(e)}",
                "text": ""
            }

    def recognize_with_details(self, image: np.ndarray) -> List[OCRResult]:
        """识别图像中的文字，返回详细信息"""
        results: List[OCRResult] = []

        try:
            if self._paddle_enabled:
                if image.ndim == 2:
                    image = np.stack([image] * 3, axis=-1)
                for b in self.recognize_text_blocks(image):
                    text = b.get("text") or ""
                    conf = float(b.get("conf", 0)) / 100.0
                    box = (b.get("left", 0), b.get("top", 0), b.get("width", 0), b.get("height", 0))
                    results.append(
                        OCRResult(
                            text=text,
                            confidence=conf,
                            bounding_box=box,
                            block_type=self._classify_text(text),
                        )
                    )
                return results

            if self.reader is None:
                return results

            easyocr_results = self.reader.readtext(image, detail=1)

            for (bbox, text, confidence) in easyocr_results:
                ocr_result = OCRResult(
                    text=text,
                    confidence=confidence,
                    bounding_box=tuple(int(x) for x in np.asarray(bbox).flatten()[:4]),
                    block_type=self._classify_text(text),
                )
                results.append(ocr_result)

        except Exception as e:
            logger.error("OCR识别失败: %s", e)

        return results

    def recognize_text(self, image_path: str) -> Dict[str, Any]:
        """应用层：按路径识别（与 recognize_file 一致，补充 confidence）。"""
        out = self.recognize_file(image_path)
        if out.get("success") and "confidence" not in out:
            out["confidence"] = 0.0
        return out

    def recognize_text_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """应用层：从字节识别。"""
        try:
            from PIL import Image

            img = Image.open(BytesIO(image_bytes))
            if self._paddle_enabled:
                blocks = self.recognize_text_blocks(img)
                text = self._clean_text("\n".join(b["text"] for b in blocks if b.get("text")))
                confs = [float(b.get("conf", 0)) for b in blocks]
                avg = (sum(confs) / len(confs) / 100.0) if confs else 0.0
                return {"success": bool(text.strip()), "text": text, "confidence": avg}
            text = self.recognize(img)
            return {"success": bool(text.strip()), "text": text, "confidence": 0.0}
        except Exception as e:
            logger.exception("从字节 OCR 失败: %s", e)
            return {"success": False, "message": str(e), "text": "", "confidence": 0.0}

    def recognize_trademark(self, image_path: str) -> Dict[str, Any]:
        """商标图识别（当前与通用识别相同）。"""
        return self.recognize_text(image_path)

    def recognize_product(self, image_path: str) -> Dict[str, Any]:
        """产品信息图识别（当前与通用识别相同）。"""
        return self.recognize_text(image_path)

    def get_active_ocr_backend(self) -> str:
        """当前主引擎名称（用于诊断）。"""
        if self._paddle_enabled:
            return "paddleocr"
        if self.reader is not None:
            return "easyocr"
        if self.tesseract_available:
            return "tesseract"
        return "none"

    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """从OCR文本中提取结构化数据"""
        structured_data = {
            "purchase_unit": None,
            "contact_person": None,
            "contact_phone": None,
            "purchase_date": None,
            "order_number": None,
            "total_amount": None,
            "products": [],
            "raw_text": text
        }

        unit_match = re.search(r'购货单位[：:]\s*(.+?)(?:\n|$)', text)
        if unit_match:
            structured_data["purchase_unit"] = unit_match.group(1).strip()

        contact_match = re.search(r'联系人[：:]\s*(.+?)(?:\n|$)', text)
        if contact_match:
            structured_data["contact_person"] = contact_match.group(1).strip()

        phone_match = re.search(r'联系电话[：:]\s*([\d\-\+]+)', text)
        if phone_match:
            structured_data["contact_phone"] = phone_match.group(1).strip()

        date_match = re.search(r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)', text)
        if date_match:
            structured_data["purchase_date"] = date_match.group(1)

        order_match = re.search(r'订单编号[：:]\s*(.+?)(?:\n|$)', text)
        if order_match:
            structured_data["order_number"] = order_match.group(1).strip()

        amount_match = re.search(r'合计[：:]\s*([\d\.]+)', text)
        if amount_match:
            try:
                structured_data["total_amount"] = float(amount_match.group(1))
            except ValueError:
                pass

        product_pattern = r'([A-Za-z0-9]+)\s+(.+?)\s+(\d+)\s+([\d\.]+)\s+([\d\.]+)'
        for match in re.finditer(product_pattern, text):
            product = {
                "model": match.group(1),
                "name": match.group(2),
                "quantity": int(match.group(3)),
                "unit_price": float(match.group(4)),
                "total_price": float(match.group(5))
            }
            structured_data["products"].append(product)

        return structured_data

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """分析文本内容"""
        analysis = {
            "text_type": "unknown",
            "confidence": 0.0,
            "detected_fields": {},
            "missing_fields": [],
            "suggestions": []
        }

        if not text:
            return analysis

        keywords = {
            "order": ["订单", "订购", "下单"],
            "shipment": ["发货", "送货"],
            "payment": ["付款", "支付", "金额", "合计"],
            "product": ["产品", "型号", "规格"],
            "customer": ["客户", "购货单位"],
            "contact": ["联系人", "电话"],
            "date": ["日期", "时间"],
        }

        type_scores = {}
        for type_name, kws in keywords.items():
            score = sum(1 for kw in kws if kw in text)
            type_scores[type_name] = score

        if type_scores:
            max_type = max(type_scores, key=type_scores.get)
            if type_scores[max_type] > 0:
                analysis["text_type"] = max_type
                analysis["confidence"] = min(1.0, type_scores[max_type] / 3)

        field_patterns = {
            "purchase_unit": r'购货单位[：:]\s*(.+?)(?:\n|$)',
            "contact_person": r'联系人[：:]\s*(.+?)(?:\n|$)',
            "phone": r'电话[：:]\s*([\d\-\+]+)',
            "date": r'(\d{4}[年-]\d{1,2}[月-]\d{1,2}[日]?)',
            "order_id": r'订单[编号]?[：:]\s*(.+?)(?:\n|$)',
            "total": r'合计[：:]\s*([\d\.]+)',
        }

        for field, pattern in field_patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                analysis["detected_fields"][field] = value.strip()

        essential_fields = ["purchase_unit", "contact_person", "date"]
        for field in essential_fields:
            if field not in analysis["detected_fields"]:
                analysis["missing_fields"].append(field)

        if analysis["text_type"] == "unknown":
            analysis["suggestions"].append("文本类型不明确，请手动确认")

        return analysis

    def _clean_text(self, text: str) -> str:
        """清理识别出的文字"""
        if not text:
            return ""

        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        return '\n'.join(cleaned_lines)

    def _classify_text(self, text: str) -> str:
        """分类文本类型"""
        if not text:
            return "unknown"

        if re.match(r'^[\d\.\,\-\+]+$', text):
            return "number"

        date_patterns = [r'\d{4}[-年]\d{1,2}[-月]\d{1,2}', r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}']
        for pattern in date_patterns:
            if re.search(pattern, text):
                return "date"

        if re.search(r'[\d\.]+\s*(元|¥|dollar|$|€)', text):
            return "amount"

        if re.match(r'^[\d\-\+\(\)]{7,}$', text):
            return "phone"

        return "text"


ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    return ocr_service
