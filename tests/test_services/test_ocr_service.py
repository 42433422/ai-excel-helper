"""
OCR服务单元测试
"""

import pytest
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from app.services.ocr_service import OCRService


@pytest.fixture
def service():
    """创建OCR服务实例"""
    return OCRService()


class TestExtractStructuredData:
    """extract_structured_data 方法测试"""

    def test_extract_customer_info(self, service):
        """测试成功提取客户信息"""
        text = """
        购货单位：深圳市某某公司
        联系人：张三
        联系电话：138-1234-5678
        """
        result = service.extract_structured_data(text)

        assert result["purchase_unit"] == "深圳市某某公司"
        assert result["contact_person"] == "张三"
        assert result["contact_phone"] == "138-1234-5678"

    def test_extract_purchase_date(self, service):
        """测试提取购买日期"""
        text = "购货单位：广州某某公司\n订购日期：2024-01-15"
        result = service.extract_structured_data(text)

        assert result["purchase_date"] == "2024-01-15"

    def test_extract_order_number(self, service):
        """测试提取订单编号"""
        text = "订单编号：ORD202401150001\n购货单位：测试公司"
        result = service.extract_structured_data(text)

        assert result["order_number"] == "ORD202401150001"

    def test_extract_products(self, service):
        """测试提取产品信息"""
        text = """
        购货单位：测试公司
        ABC001 产品A 10 100.00 1000.00
        DEF002 产品B 5 50.00 250.00
        """
        result = service.extract_structured_data(text)

        assert len(result["products"]) == 2
        assert result["products"][0]["model"] == "ABC001"
        assert result["products"][0]["name"] == "产品A"
        assert result["products"][0]["quantity"] == 10
        assert result["products"][0]["unit_price"] == 100.00
        assert result["products"][0]["total_price"] == 1000.00
        assert result["products"][1]["model"] == "DEF002"
        assert result["products"][1]["quantity"] == 5

    def test_extract_total_amount(self, service):
        """测试提取金额信息"""
        text = """
        购货单位：测试公司
        合计：1250.50
        """
        result = service.extract_structured_data(text)

        assert result["total_amount"] == 1250.50

    def test_extract_empty_text(self, service):
        """测试空文本"""
        result = service.extract_structured_data("")

        assert result["purchase_unit"] is None
        assert result["contact_person"] is None
        assert result["contact_phone"] is None
        assert result["purchase_date"] is None
        assert result["order_number"] is None
        assert result["total_amount"] is None
        assert result["products"] == []
        assert result["raw_text"] == ""

    def test_extract_no_matching_fields(self, service):
        """测试无匹配字段"""
        text = "这是一段没有任何匹配格式的文本内容"
        result = service.extract_structured_data(text)

        assert result["purchase_unit"] is None
        assert result["contact_person"] is None
        assert result["products"] == []

    def test_extract_partial_data(self, service):
        """测试部分数据提取"""
        text = """
        购货单位：部分公司
        联系人：李四
        """
        result = service.extract_structured_data(text)

        assert result["purchase_unit"] == "部分公司"
        assert result["contact_person"] == "李四"
        assert result["contact_phone"] is None
        assert result["purchase_date"] is None

    def test_extract_chinese_date_format(self, service):
        """测试中文日期格式"""
        text = "购货单位：公司A\n2024年1月20日"
        result = service.extract_structured_data(text)

        assert result["purchase_date"] == "2024年1月20日"

    def test_extract_invalid_amount(self, service):
        """测试无效金额格式"""
        text = "合计：abc"
        result = service.extract_structured_data(text)

        assert result["total_amount"] is None

    def test_extract_raw_text_preserved(self, service):
        """测试原始文本被保留"""
        text = "购货单位：测试公司\n这是原始文本内容"
        result = service.extract_structured_data(text)

        assert result["raw_text"] == text


class TestAnalyzeText:
    """analyze_text 方法测试"""

    def test_identify_order_type(self, service):
        """测试识别订单类型"""
        text = "订单编号：12345\n订购产品：显示器\n订单金额：2000"
        result = service.analyze_text(text)

        assert result["text_type"] == "order"
        assert result["confidence"] > 0

    def test_identify_shipment_type(self, service):
        """测试识别发货单类型"""
        text = "发货单：送货单001\n送货地址：深圳市\n发货日期：2024-01-01"
        result = service.analyze_text(text)

        assert result["text_type"] == "shipment"
        assert result["confidence"] > 0

    def test_identify_payment_type(self, service):
        """测试识别支付类型"""
        text = "付款金额：5000元\n支付方式：银行转账\n合计：5000"
        result = service.analyze_text(text)

        assert result["text_type"] == "payment"

    def test_identify_product_type(self, service):
        """测试识别产品类型"""
        text = "产品规格：型号X\n产品名称：测试产品\n规格说明：标准"
        result = service.analyze_text(text)

        assert result["text_type"] == "product"

    def test_identify_customer_type(self, service):
        """测试识别客户类型"""
        text = "客户名称：某某公司\n购货单位：采购部"
        result = service.analyze_text(text)

        assert result["text_type"] == "customer"

    def test_detect_missing_fields(self, service):
        """测试检测缺失字段"""
        text = "这是一些没有关键字段的文本内容"
        result = service.analyze_text(text)

        assert "purchase_unit" in result["missing_fields"]
        assert "contact_person" in result["missing_fields"]
        assert "date" in result["missing_fields"]

    def test_provide_suggestions_unknown_type(self, service):
        """测试未知类型提供建议"""
        text = "这是一段完全没有任何关键词的普通文本"
        result = service.analyze_text(text)

        assert "suggestions" in result
        assert any("手动确认" in s for s in result["suggestions"])

    def test_analyze_empty_text(self, service):
        """测试空文本分析"""
        result = service.analyze_text("")

        assert result["text_type"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["detected_fields"] == {}
        assert result["missing_fields"] == []

    def test_detect_all_essential_fields(self, service):
        """测试所有必要字段都存在"""
        text = """
        购货单位：测试公司
        联系人：张三
        2024-01-15
        """
        result = service.analyze_text(text)

        assert len(result["missing_fields"]) == 0
        assert "purchase_unit" in result["detected_fields"]
        assert "contact_person" in result["detected_fields"]
        assert "date" in result["detected_fields"]

    def test_detect_purchase_unit_field(self, service):
        """测试检测购货单位字段"""
        text = "购货单位：某某公司"
        result = service.analyze_text(text)

        assert "purchase_unit" in result["detected_fields"]

    def test_detect_phone_field(self, service):
        """测试检测电话字段"""
        text = "联系电话：138-1234-5678"
        result = service.analyze_text(text)

        assert "phone" in result["detected_fields"]

    def test_detect_total_field(self, service):
        """测试检测金额字段"""
        text = "合计：1500.00"
        result = service.analyze_text(text)

        assert "total" in result["detected_fields"]

    def test_confidence_calculation(self, service):
        """测试置信度计算"""
        text = "订单编号：001\n订购日期：2024-01-01\n订单金额：1000"
        result = service.analyze_text(text)

        assert result["confidence"] <= 1.0
        assert result["confidence"] >= 0.0


class TestCleanText:
    """_clean_text 方法测试"""

    def test_clean_normal_text(self, service):
        """测试清理普通文本"""
        text = "  第一行  \n  第二行  \n  第三行  "
        result = service._clean_text(text)

        assert result == "第一行\n第二行\n第三行"

    def test_clean_empty_text(self, service):
        """测试清理空文本"""
        result = service._clean_text("")

        assert result == ""

    def test_clean_text_with_only_whitespace(self, service):
        """测试只包含空白的文本"""
        result = service._clean_text("   \n\n   \t   ")

        assert result == ""

    def test_clean_text_remove_empty_lines(self, service):
        """测试移除空行"""
        text = "第一行\n\n第二行\n\n\n第三行"
        result = service._clean_text(text)

        assert result == "第一行\n第二行\n第三行"

    def test_clean_text_preserve_content(self, service):
        """测试保留文本内容"""
        text = "购货单位：深圳公司\n联系人：张三\n电话：13812345678"
        result = service._clean_text(text)

        assert "购货单位" in result
        assert "联系人" in result


class TestClassifyText:
    """_classify_text 方法测试"""

    def test_classify_number(self, service):
        """测试数字分类"""
        text = "123456"
        result = service._classify_text(text)

        assert result == "number"

    def test_classify_date_chinese_format(self, service):
        """测试中文日期分类"""
        text = "2024年1月15日"
        result = service._classify_text(text)

        assert result == "date"

    def test_classify_date_with_slash(self, service):
        """测试斜杠日期格式"""
        text = "2024/01/15"
        result = service._classify_text(text)

        assert result == "date"

    def test_classify_date_with_year(self, service):
        """测试带年份的日期"""
        text = "2024年1月15日"
        result = service._classify_text(text)

        assert result == "date"

    def test_classify_date_short_format(self, service):
        """测试短日期格式"""
        text = "01/15/2024"
        result = service._classify_text(text)

        assert result == "date"

    def test_classify_amount_yuan(self, service):
        """测试人民币金额"""
        text = "100元"
        result = service._classify_text(text)

        assert result == "amount"

    def test_classify_amount_yen(self, service):
        """测试日元金额"""
        text = "5000 dollar"
        result = service._classify_text(text)

        assert result == "amount"

    def test_classify_amount_dollar(self, service):
        """测试美元金额"""
        text = "$100.50"
        result = service._classify_text(text)

        assert result == "amount"

    def test_classify_text(self, service):
        """测试普通文本分类"""
        text = "购货单位：测试公司"
        result = service._classify_text(text)

        assert result == "text"

    def test_classify_empty_text(self, service):
        """测试空文本分类"""
        result = service._classify_text("")

        assert result == "unknown"

    def test_classify_text_with_numbers(self, service):
        """测试混合数字的文本"""
        text = "订单ABC"
        result = service._classify_text(text)

        assert result == "text"


class TestOCRServiceIntegration:
    """OCR服务集成测试"""

    @pytest.fixture
    def sample_order_text(self):
        """示例订单文本"""
        return """
        购货单位：深圳市某某科技有限公司
        联系人：张三
        联系电话：138-1234-5678
        订单编号：ORD202401150001
        订购日期：2024-01-15
        ABC001 显示器 10 1000.00 10000.00
        DEF002 键盘 20 50.00 1000.00
        合计：11000.00
        """

    def test_full_workflow(self, service, sample_order_text):
        """测试完整工作流"""
        cleaned_text = service._clean_text(sample_order_text)
        assert cleaned_text

        analysis = service.analyze_text(cleaned_text)
        assert analysis["text_type"] in ["order", "shipment", "payment", "product", "customer"]

        structured = service.extract_structured_data(cleaned_text)
        assert structured["purchase_unit"] == "深圳市某某科技有限公司"
        assert structured["contact_person"] == "张三"
        assert structured["order_number"] == "ORD202401150001"
        assert len(structured["products"]) == 2
        assert structured["total_amount"] == 11000.00

    def test_mixed_text_analysis(self, service):
        """测试混合文本分析"""
        text = """
        订单编号：12345
        购货单位：测试公司
        联系人：李四
        2024-01-01
        金额：5000元
        """
        analysis = service.analyze_text(text)

        assert analysis["text_type"] in ["order", "payment", "customer"]
        assert len(analysis["missing_fields"]) == 0

    def test_incomplete_document(self, service):
        """测试不完整文档"""
        text = "这是一份不完整的文档，只有一些基本信息"
        analysis = service.analyze_text(text)
        structured = service.extract_structured_data(text)

        assert len(analysis["missing_fields"]) > 0
        assert analysis["text_type"] == "unknown"
        assert all(v is None for v in [
            structured["purchase_unit"],
            structured["contact_person"],
            structured["order_number"]
        ])
