"""
OCR服务模块

提供图像文字识别、结构化数据提取等业务逻辑。
"""

import logging
import os
import re
from dataclasses import dataclass
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
        self._initialize_reader()

    def _initialize_reader(self):
        """初始化OCR读取器"""
        try:
            import easyocr
            self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=self.use_gpu)
            logger.info("EasyOCR 初始化成功")
        except ImportError:
            logger.warning("EasyOCR 未安装，尝试使用 Tesseract")
            self._init_tesseract()
        except Exception as e:
            logger.error(f"OCR初始化失败: {e}")
            self.reader = None

    def _init_tesseract(self):
        """初始化Tesseract"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("Tesseract OCR 初始化成功")
        except (ImportError, Exception):
            logger.warning("Tesseract 不可用")
            self.tesseract_available = False

    def recognize(self, image) -> str:
        """
        识别图像中的文字

        Args:
            image: PIL Image 或 numpy数组格式的图像

        Returns:
            识别出的文字
        """
        if self.reader is None and not self.tesseract_available:
            logger.error("OCR引擎未初始化")
            return ""

        try:
            if hasattr(image, 'convert'):
                image_array = np.array(image)
            else:
                image_array = image

            if self.reader is not None:
                results = self.reader.readtext(image_array, detail=0)
                text = '\n'.join(results)
                return self._clean_text(text)

            if self.tesseract_available:
                from PIL import Image
                pil_image = Image.fromarray(image_array)
                import pytesseract
                text = pytesseract.image_to_string(pil_image, lang='chi_sim+eng')
                return self._clean_text(text)

        except Exception as e:
            logger.error(f"OCR识别失败: {e}")

        return ""

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
        results = []

        if self.reader is None:
            return results

        try:
            easyocr_results = self.reader.readtext(image, detail=1)

            for (bbox, text, confidence) in easyocr_results:
                ocr_result = OCRResult(
                    text=text,
                    confidence=confidence,
                    bounding_box=tuple(bbox),
                    block_type=self._classify_text(text)
                )
                results.append(ocr_result)

        except Exception as e:
            logger.error(f"OCR识别失败: {e}")

        return results

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
