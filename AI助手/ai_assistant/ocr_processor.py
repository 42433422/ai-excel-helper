# OCR文字识别模块
import re
import logging
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR识别结果"""
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x1, y1, x2, y2
    block_type: str = "text"  # text, number, date, etc.


class OCRProcessor:
    """OCR处理器"""

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.reader = None
        self._initialize_reader()

    def _initialize_reader(self):
        """初始化OCR读取器"""
        try:
            import easyocr
            self.reader = easyocr.Reader(
                ['ch_sim', 'en'],
                gpu=self.use_gpu
            )
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
            from pytesseract import image_to_string

            # 检查Tesseract是否可用
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            logger.info("Tesseract OCR 初始化成功")

        except (ImportError, pytesseract.TesseractNotFoundError):
            logger.warning("Tesseract 不可用，将使用备用识别方法")
            self.tesseract_available = False

    def recognize(self, image) -> str:
        """
        识别图像中的文字

        Args:
            image: PIL Image 或 numpy数组格式的图像

        Returns:
            识别出的文字
        """
        if self.reader is None and not getattr(self, 'tesseract_available', False):
            logger.error("OCR引擎未初始化")
            return ""

        try:
            # 转换为numpy数组（如果传入的是PIL Image）
            if hasattr(image, 'convert'):
                # PIL Image
                image_array = np.array(image)
            else:
                # 已经是numpy数组
                image_array = image

            # 使用EasyOCR识别
            if self.reader is not None:
                results = self.reader.readtext(image_array, detail=0)
                text = '\n'.join(results)
                return self._clean_text(text)

            # 使用Tesseract识别
            if getattr(self, 'tesseract_available', False):
                import pytesseract
                from PIL import Image

                pil_image = Image.fromarray(image)
                text = pytesseract.image_to_string(pil_image, lang='chi_sim+eng')
                return self._clean_text(text)

        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""

        return ""

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

    def _clean_text(self, text: str) -> str:
        """清理识别出的文字"""
        if not text:
            return ""

        # 移除多余的空白字符
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        return '\n'.join(cleaned_lines)

    def _classify_text(self, text: str) -> str:
        """分类文本类型"""
        if not text:
            return "unknown"

        # 检测是否为数字
        if re.match(r'^[\d\.\,\-\+]+$', text):
            return "number"

        # 检测是否为日期
        date_patterns = [
            r'\d{4}[-年]\d{1,2}[-月]\d{1,2}',
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
        ]
        for pattern in date_patterns:
            if re.search(pattern, text):
                return "date"

        # 检测是否为金额
        if re.search(r'[\d\.]+\s*(元|¥|dollar|$|€)', text):
            return "amount"

        # 检测是否为联系方式
        if re.match(r'^[\d\-\+\(\)]{7,}$', text):
            return "phone"

        return "text"

    def extract_structured_data(self, text: str) -> Dict:
        """从OCR文本中提取结构化数据"""
        structured_data = {
            "purchase_unit": None,  # 购货单位
            "contact_person": None,  # 联系人
            "contact_phone": None,  # 联系电话
            "purchase_date": None,  # 购买日期
            "order_number": None,  # 订单编号
            "total_amount": None,  # 总金额
            "products": [],  # 产品列表
            "raw_text": text
        }

        # 提取购货单位
        unit_match = re.search(r'购货单位[：:]\s*(.+?)(?:\n|$)', text)
        if unit_match:
            structured_data["purchase_unit"] = unit_match.group(1).strip()

        # 提取联系人
        contact_match = re.search(r'联系人[：:]\s*(.+?)(?:\n|$)', text)
        if contact_match:
            structured_data["contact_person"] = contact_match.group(1).strip()

        # 提取联系电话
        phone_match = re.search(r'联系电话[：:]\s*([\d\-\+]+)', text)
        if phone_match:
            structured_data["contact_phone"] = phone_match.group(1).strip()

        # 提取日期
        date_match = re.search(r'(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)', text)
        if date_match:
            structured_data["purchase_date"] = date_match.group(1)

        # 提取订单编号
        order_match = re.search(r'订单编号[：:]\s*(.+?)(?:\n|$)', text)
        if order_match:
            structured_data["order_number"] = order_match.group(1).strip()

        # 提取总金额
        amount_match = re.search(r'合计[：:]\s*([\d\.]+)', text)
        if amount_match:
            try:
                structured_data["total_amount"] = float(amount_match.group(1))
            except ValueError:
                pass

        # 提取产品信息（简单模式匹配）
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

    def extract_numbers(self, text: str) -> List[str]:
        """提取所有数字"""
        return re.findall(r'[\d\.]+', text)

    def extract_dates(self, text: str) -> List[str]:
        """提取所有日期"""
        date_patterns = [
            r'\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?',
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
        ]

        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text))

        return dates

    def extract_amounts(self, text: str) -> List[Dict]:
        """提取金额信息"""
        amounts = []
        amount_pattern = r'([\d\.]+)\s*(元|¥|dollar|$|€)'

        for match in re.finditer(amount_pattern, text):
            amounts.append({
                "value": float(match.group(1)),
                "currency": match.group(2)
            })

        return amounts

    def verify_readability(self, text: str) -> Dict:
        """验证文本的可读性和完整性"""
        verification = {
            "readable": True,
            "confidence": 1.0,
            "issues": [],
            "suggestions": []
        }

        if not text:
            verification["readable"] = False
            verification["issues"].append("未检测到文字")
            verification["confidence"] = 0.0
            return verification

        # 检查文本长度
        if len(text) < 10:
            verification["issues"].append("文本过短，可能识别不完整")
            verification["confidence"] *= 0.8

        # 检查是否包含乱码
        if re.search(r'[■□◆◇○◎●★☆♡♠♣♥♦♩♪♫♬]', text):
            verification["issues"].append("可能存在乱码")
            verification["confidence"] *= 0.7

        # 检查关键字段
        required_fields = ["购货单位", "联系人", "日期"]
        for field in required_fields:
            if field not in text:
                verification["suggestions"].append(f"建议检查{field}字段")

        # 检查完整性
        if not re.search(r'\d{4}', text):
            verification["issues"].append("未检测到年份，可能日期识别有误")
            verification["confidence"] *= 0.9

        verification["confidence"] = max(0.0, verification["confidence"])
        verification["readable"] = verification["confidence"] > 0.5

        return verification


class TextAnalyzer:
    """文本分析器"""

    def __init__(self):
        self.keywords = {
            "order": ["订单", "订购", "下单", "Order", "ORDER"],
            "shipment": ["发货", "送货", "Shipment", "SHIPMENT"],
            "payment": ["付款", "支付", "Payment", "PAYMENT", "金额", "合计"],
            "product": ["产品", "型号", "规格", "Product", "PRODUCT"],
            "customer": ["客户", "顾客", "Customer", "CUSTOMER", "购货单位"],
            "contact": ["联系人", "电话", "Contact", "CONTACT"],
            "date": ["日期", "Date", "DATE", "时间"],
        }

    def analyze(self, text: str) -> Dict:
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

        text_lower = text.lower()

        # 检测文本类型
        type_scores = {}
        for type_name, keywords in self.keywords.items():
            if type_name in ["order", "shipment", "payment", "product", "customer", "contact", "date"]:
                score = sum(1 for kw in keywords if kw in text)
                type_scores[type_name] = score

        if type_scores:
            max_type = max(type_scores, key=type_scores.get)
            if type_scores[max_type] > 0:
                analysis["text_type"] = max_type
                analysis["confidence"] = min(1.0, type_scores[max_type] / 3)

        # 检测字段
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

        # 检查缺失字段
        essential_fields = ["purchase_unit", "contact_person", "date"]
        for field in essential_fields:
            if field not in analysis["detected_fields"]:
                analysis["missing_fields"].append(field)

        # 生成建议
        if "payment" in type_scores and type_scores["payment"] > 0:
            if "total" not in analysis["detected_fields"]:
                analysis["suggestions"].append("建议提取总金额信息")

        if analysis["text_type"] == "unknown":
            analysis["suggestions"].append("文本类型不明确，请手动确认")

        return analysis
